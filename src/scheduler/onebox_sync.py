"""OneBox Sync Worker - Migrated to ETL Layer (HUB-013)."""

import time
from datetime import datetime
from typing import List, Dict, Any, Tuple
from sqlmodel import Session, select, or_
from src.core.database import engine
from src.core.logger import get_logger
from src.core.models_db import FactSalesReportItem, DimProductVariant, DimStore, DimCustomer
from src.adapters.onebox.client import OneBoxClient
from src.config.settings import settings

logger = get_logger(__name__)

class OneBoxSyncWorker:
    """
    Syncs sales from the FactSalesReportItem table to OneBox CRM.
    Groups line items by receipt_uuid to create single orders in OneBox.
    """

    def __init__(self):
        self.client = OneBoxClient(
            domain=settings.onebox_url,
            login=settings.onebox_login,
            token=settings.onebox_api_key
        )

    def run_sync_batch(self, limit: int = 50):
        """Processes a batch of unsynced sales items, filtering and grouping by receipt."""
        with Session(engine) as session:
            # 1. Fetch pending items joined with dimensions (Enriched layer logic)
            # Only valid receipts: posted=True, deleted=False
            # Using or_ comparison for characteristic_uuid to handle nulls correctly
            statement = (
                select(FactSalesReportItem, DimProductVariant, DimStore, DimCustomer)
                .join(
                    DimProductVariant, 
                    (FactSalesReportItem.product_uuid == DimProductVariant.product_uuid) & 
                    (
                        (FactSalesReportItem.characteristic_uuid == DimProductVariant.characteristic_uuid) |
                        ((FactSalesReportItem.characteristic_uuid == None) & (DimProductVariant.characteristic_uuid == None))
                    ),
                    isouter=True
                )
                .join(DimStore, FactSalesReportItem.store_uuid == DimStore.store_uuid, isouter=True)
                .join(DimCustomer, FactSalesReportItem.customer_uuid == DimCustomer.customer_uuid, isouter=True)
                .where(
                    or_(
                        FactSalesReportItem.onebox_status == "pending",
                        FactSalesReportItem.onebox_status == "failed"
                    ),
                    FactSalesReportItem.receipt_posted == True,
                    FactSalesReportItem.receipt_deleted == False
                )
                .order_by(FactSalesReportItem.receipt_datetime)
                .limit(limit * 5) # Fetch enough lines to group by receipt
            )
            
            results = session.exec(statement).all()

            if not results:
                return

            # 2. Group items by receipt_uuid
            receipt_groups: Dict[Any, List[Tuple[FactSalesReportItem, DimProductVariant, DimStore, DimCustomer]]] = {}
            for fact, variant, store, customer in results:
                if fact.receipt_uuid not in receipt_groups:
                    receipt_groups[fact.receipt_uuid] = []
                receipt_groups[fact.receipt_uuid].append((fact, variant, store, customer))

            logger.info("onebox_sync_batch_start", unique_receipts=len(receipt_groups))

            for receipt_uuid, lines_data in receipt_groups.items():
                # Skip if any line has qty < 0 (return receipt)
                if any(f.qty < 0 for f, _, _, _ in lines_data):
                    logger.info("onebox_sync_skip_return", receipt_uuid=str(receipt_uuid))
                    for f, _, _, _ in lines_data:
                        f.onebox_status = "ignored_return"
                        f.updated_at = datetime.utcnow()
                    continue
                
                # Skip if not personalized
                if lines_data[0][0].customer_uuid is None:
                    logger.info("onebox_sync_skip_anonymous", receipt_uuid=str(receipt_uuid))
                    for f, _, _, _ in lines_data:
                        f.onebox_status = "ignored_anonymous"
                        f.updated_at = datetime.utcnow()
                    continue

                self._sync_single_receipt(session, receipt_uuid, lines_data)

            session.commit()

    def _sync_single_receipt(self, session: Session, receipt_uuid: Any, lines_data: List[Tuple[FactSalesReportItem, DimProductVariant, DimStore, DimCustomer]]):
        """Groups lines and pushes a single order to OneBox."""
        try:
            facts = [f for f, _, _, _ in lines_data]
            
            # Mark as processing to avoid race conditions with parallel workers
            for fact in facts:
                fact.onebox_status = "processing"
            session.commit()

            # 1. Upsert Products to OneBox
            product_upsert_payload = []
            for fact, variant, store, customer in lines_data:
                # Use enriched name if variant was found, else placeholder
                if variant:
                    p_name = variant.product_name
                    c_name = variant.characteristic_name or ""
                    # Anton: Use direct characteristic_article from 1C if available, otherwise fallback
                    article = variant.characteristic_article or variant.article or ""
                else:
                    p_name = f"Product {fact.product_uuid}"
                    c_name = ""
                    article = ""
                
                # Final SKU for OneBox
                sku = article.strip() if article else str(fact.characteristic_uuid or fact.product_uuid)
                full_name = f"{p_name} {c_name}".strip()
                
                product_upsert_payload.append({
                    "name": full_name,
                    "articul": sku,
                    "price": fact.price,
                    "findbyArray": ["articul"]
                })
                logger.info("onebox_sync_prep_product", receipt_uuid=str(receipt_uuid), articul=sku, name=full_name)
            
            # Upsert all products in one batch request
            prod_response = self.client.set_products(product_upsert_payload)
            if prod_response.get("status") != 1:
                raise ValueError(f"Failed to upsert products: {prod_response.get('errorArray')}")
            onebox_product_ids = prod_response.get("dataArray", [])
            if len(onebox_product_ids) != len(product_upsert_payload):
                raise ValueError(f"Product ID count mismatch: got {len(onebox_product_ids)}, expected {len(product_upsert_payload)}")

            # 1.1. Upsert Customer to OneBox (HUB-014)
            customer = lines_data[0][3]
            onebox_customer_id = None
            customer_first_name = ""
            customer_last_name = ""

            # Anonymous sale (null UUID) — skip, no deal needed in OneBox
            NULL_UUID = "00000000-0000-0000-0000-000000000000"
            if str(facts[0].customer_uuid or "") == NULL_UUID:
                for fact in facts:
                    fact.onebox_status = "ignored_anonymous"
                    fact.sync_error = None
                    fact.updated_at = datetime.utcnow()
                logger.info("onebox_sync_ignored_anonymous", receipt_uuid=str(receipt_uuid))
                return

            # If receipt has customer_uuid, but customer is missing in dim_customers,
            # postpone sync and retry on next cycle.
            if facts[0].customer_uuid is not None and (not customer or (not (customer.customer_phone or '').strip() and not (customer.customer_name or '').strip())):
                for fact in facts:
                    fact.onebox_status = "pending"
                    fact.sync_error = "missing_customer_in_dim"
                    fact.updated_at = datetime.utcnow()
                logger.warning("onebox_sync_missing_customer_dim_retry", receipt_uuid=str(receipt_uuid), customer_uuid=str(facts[0].customer_uuid))
                return
            
            if customer:
                full_name = (customer.customer_name or "Невідомий клієнт").strip()
                phone = (customer.customer_phone or "").strip()

                # Split Name: Assuming "Last First Middle" or "Last First"
                name_parts = full_name.split()
                if len(name_parts) >= 2:
                    customer_last_name = name_parts[0]
                    customer_first_name = " ".join(name_parts[1:])
                else:
                    customer_last_name = ""
                    customer_first_name = full_name

                # STEP 0: Use cached onebox_contact_id if already known — skip API search
                if customer.onebox_contact_id:
                    onebox_customer_id = customer.onebox_contact_id
                    logger.info("onebox_customer_from_cache", id=onebox_customer_id,
                                customer_uuid=str(customer.customer_uuid))

                # STEP 1: Search for existing contact by phone to avoid duplicates
                if not onebox_customer_id and phone:
                    # Search by phone often behaves inconsistently in API v2
                    # We will also try to search by namelast if we have it
                    clean_search_phone = phone.replace("+", "").replace("-", "").replace(" ", "").replace("(", "").replace(")", "").strip()
                    # Also try search without 38
                    short_phone = clean_search_phone[2:] if clean_search_phone.startswith("38") else clean_search_phone
                    
                    search_res = self.client.get_contacts({"filter": {"phones": [clean_search_phone]}, "fields": ["id", "name", "namelast", "phones", "phone"]})
                    
                    if search_res.get("status") == 1:
                        candidates = search_res.get("dataArray", []) or []
                        
                        # Try short phone if nothing found
                        if not candidates:
                            search_res_short = self.client.get_contacts({"filter": {"phones": [short_phone]}, "fields": ["id", "name", "namelast", "phones", "phone"]})
                            if search_res_short.get("status") == 1:
                                candidates = search_res_short.get("dataArray", []) or []
                        
                        # If search by phone returned nothing or trash, try by namelast + name
                        search_res_name = self.client.get_contacts({"filter": {"namelast": customer_last_name}, "fields": ["id", "name", "namelast", "phones", "phone"]})
                        if search_res_name.get("status") == 1:
                             name_candidates = search_res_name.get("dataArray", []) or []
                             # Merge candidates and remove duplicates by ID
                             existing_ids = {c.get("id") for c in candidates}
                             for nc in name_candidates:
                                 if nc.get("id") not in existing_ids:
                                     candidates.append(nc)

                        # Clean target phone
                        clean_phone = phone.replace("+", "").replace("-", "").replace(" ", "").replace("(", "").replace(")", "").strip()

                        # Sort candidates: prioritize those with non-empty phones or specific original ID if found
                        candidates.sort(key=lambda x: (len(x.get("phones", []) or []), str(x.get("id")) == "46741"), reverse=True)

                        # Filter specifically for a true match
                        for candidate in candidates:
                            c_id = str(candidate.get("id"))
                            c_name = (candidate.get("name") or "").strip()
                            c_last = (candidate.get("namelast") or "").strip()
                            c_phones = candidate.get("phones", []) or []
                            c_phone = (candidate.get("phone") or "").strip()

                            # Hardcoded safeguard for restapi or system IDs
                            if c_name == "restapi" or c_id == "1":
                                continue
                            
                            clean_c_phones = [p.replace("+", "").replace("-", "").replace(" ", "").replace("(", "").replace(")", "").strip() for p in c_phones if p]
                            clean_c_phone = c_phone.replace("+", "").replace("-", "").replace(" ", "").replace("(", "").replace(")", "").strip()

                            # Match logic:
                            # 1. Exact phone match in the list of phones
                            # 2. Or exact Name + LastName match
                            phone_match = (clean_phone in clean_c_phones or (clean_phone == clean_c_phone and clean_phone != ""))
                            name_match = (c_last == customer_last_name and c_name == customer_first_name)

                            if phone_match or name_match:
                                onebox_customer_id = c_id
                                customer_first_name = c_name
                                customer_last_name = c_last
                                logger.info("onebox_customer_found_existing", id=onebox_customer_id, phone=phone, name=f"{c_last} {c_name}")
                                break

                # STEP 2: Only upsert/create if not found by phone
                if not onebox_customer_id:
                    customer_payload_item = {
                        "name": customer_first_name,
                        "namelast": customer_last_name,
                        "phones": [clean_search_phone] if phone else [],
                        "phone": clean_search_phone if phone else "",
                        "externalid": f"baf_{customer.customer_uuid}",
                        "findbyArray": ["externalid", "phone"]
                    }
                    if customer.birth_date:
                        customer_payload_item["bdate"] = customer.birth_date.strftime("%Y-%m-%d")
                    customer_payload = [customer_payload_item]
                    cust_response = self.client.set_contacts(customer_payload)
                    if cust_response.get("status") != 1:
                        logger.warning("onebox_customer_upsert_failed", error=cust_response.get("errorArray"))
                    else:
                        onebox_customer_id = str(cust_response.get("dataArray", [None])[0])

                # STEP 3: Cache onebox_contact_id in dim_customers for future calls
                if onebox_customer_id and (not customer.onebox_contact_id):
                    customer.onebox_contact_id = onebox_customer_id
                    customer.onebox_synced_at = datetime.utcnow()
                    session.add(customer)

            # 1.5. Prepare Client Phone and Store
            client_phone = customer.customer_phone if customer and customer.customer_phone else "+380000000000"
            store_name_raw = lines_data[0][2].store_name if lines_data[0][2] else "Невідомий магазин"
            
            # Store Mapping (BAF Name -> OneBox Dropdown Label)
            store_mapping = {
                "Лесі Українки": "Лесі Українки",
                "Днепр": "Дніпро",
                "Дніпро": "Дніпро",
                "River Mall": "River Mall",
                "Блокбастер": "Blockbuster",
                "Blockbuster": "Blockbuster",
                "Corner River": "Corner RiverMall",
                "Corner RiverMall": "Corner RiverMall",
                "Respublika": "Respublika"
            }
            onebox_store_label = store_mapping.get(store_name_raw)

            # 2. Prepare Order Payload
            order_products = []
            
            # Anton: Naming convention should be just the index and number (e.g. W04760)
            # Receipt numbers come as "НФНФ-W04760"
            raw_number = facts[0].receipt_number or str(receipt_uuid)
            clean_number = raw_number.split("-")[-1] if "-" in raw_number else raw_number

            for idx, (fact, variant, store, customer) in enumerate(lines_data):
                # Using line_amount to account for discounts applied in BAF
                actual_price = round(float(fact.line_amount) / float(fact.qty), 2) if fact.qty and float(fact.qty) != 0 else float(fact.price)
                
                order_products.append({
                    "productinfo": {
                        "id": str(onebox_product_ids[idx])
                    },
                    "count": fact.qty,
                    "price": actual_price,
                    "comment": f"BAF UUID: {fact.product_uuid} (base price: {fact.price})"
                })

            # OneBox Order Payload (Anton's Workflow #9)
            payload_item = {
                "name": clean_number,
                "externalid": f"1c_{receipt_uuid}",
                "workflowid": 9,
                "statusid": 54, # Проведений
                "date": facts[0].receipt_datetime.strftime("%Y-%m-%d %H:%M:%S"),
                "products": order_products,
                "deletenotupdatedproducts": True,
                "customfields": {}
            }
            
            # STEP 3: Deduplication by exact Name
            # Since findbyArray: ["name"] doesn't work reliably for closed orders in OneBox API v2 (it creates duplicates),
            # we must search manually. If it already exists, we just mark it as synced without pushing.
            existing_order_id = None
            search_order_res = self.client._post_with_retry("order/get/", {"filter": {"name": clean_number}, "fields": ["id", "name"]})
            if search_order_res.get("status") == 1:
                for o in search_order_res.get("dataArray", []):
                    if o.get("name", "").strip() == clean_number:
                        existing_order_id = str(o.get("id"))
                        logger.info("onebox_order_found_existing", id=existing_order_id, name=clean_number)
                        break
            
            if existing_order_id:
                # If it exists, DO NOT call order/set/, just mark as synced
                for fact in facts:
                    fact.onebox_status = "synced"
                    fact.onebox_order_id = existing_order_id
                    fact.onebox_synced_at = datetime.utcnow()
                    fact.sync_error = None
                    fact.updated_at = datetime.utcnow()
                logger.info("onebox_sync_skipped_already_exists", receipt_uuid=str(receipt_uuid), onebox_id=existing_order_id)
                return

            # Link Customer (HUB-014)
            if onebox_customer_id:
                # OneBox order link: Verified with support - use client.userid
                payload_item["client"] = {
                    "userid": str(onebox_customer_id)
                }
            elif customer:
                # If not found in OneBox but exists in BAF, provide info for auto-creation
                full_name = (customer.customer_name or "Невідомий клієнт").strip()
                name_parts = full_name.split()
                l_name = name_parts[0] if len(name_parts) > 0 else ""
                f_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else full_name
                phone = customer.customer_phone or "+380000000000"
                
                payload_item["client"] = {
                    "name": f_name,
                    "namelast": l_name,
                    "phone": phone,
                    "externalid": f"baf_{customer.customer_uuid}",
                    "findbyArray": ["phone", "externalid"]
                }
                # Fallback for link if creation fails/silent: user phone
                payload_item["clientphone"] = phone
            else:
                payload_item["clientphone"] = client_phone
            
            if onebox_store_label:
                payload_item["customfields"]["UF_CRM_1526724731"] = onebox_store_label

            payload = [payload_item]

            # Send to OneBox
            response = self.client.create_order(payload)

            if response.get("status") == 1:
                onebox_id = str(response["dataArray"][0])
                for fact in facts:
                    fact.onebox_status = "synced"
                    fact.onebox_order_id = onebox_id
                    fact.onebox_synced_at = datetime.utcnow()
                    fact.sync_error = None
                    fact.updated_at = datetime.utcnow()
                logger.info("onebox_sync_success", receipt_uuid=str(receipt_uuid), onebox_id=onebox_id)
            else:
                error_msg = str(response.get("errorArray", "Unknown API error"))
                for fact in facts:
                    fact.onebox_status = "failed"
                    fact.sync_error = error_msg
                    fact.updated_at = datetime.utcnow()
                logger.error("onebox_sync_failed", receipt_uuid=str(receipt_uuid), error=error_msg)

        except Exception as e:
            session.rollback()
            logger.error("onebox_sync_exception", receipt_uuid=str(receipt_uuid), error=str(e))
            for fact, _, _, _ in lines_data:
                fact.onebox_status = "failed"
                fact.sync_error = str(e)
                fact.updated_at = datetime.utcnow()
            session.commit()

if __name__ == "__main__":
    worker = OneBoxSyncWorker()
    while True:
        worker.run_sync_batch()
        time.sleep(settings.sync_interval_seconds or 60)
