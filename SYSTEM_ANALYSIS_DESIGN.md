# EcoReceipt — System Analysis and Design Notes

## 1. Problem statement
Mavailine Marketing's Chapter I identifies manual SMS order transcription, manual total calculation, repeated receipt typing/printing, and paper-based dispatch checklists as sources of errors, delays, overlooked orders, and paper waste.

## 2. Proposed solution
A role-aware web application for order capture, automated billing, stock deduction, receipt creation, fulfillment tracking, and basic reporting.

## 3. Functional requirements represented in this prototype
- Sign in using a role-based demo account.
- View an operational dashboard.
- Add/search products and view stock.
- Enter customer/store/delivery information and quantities.
- Validate stock and calculate subtotal, discount, and total.
- Save order and order items in a relational database.
- Generate a receipt record and print-friendly receipt view.
- View a delivery checklist and update order status.
- Review basic sales and top-product reports (admin only).

## 4. Non-functional requirements and design choices
- **Usability / HCI:** consistent navigation; visible labels; descriptive buttons; readable contrast; live order-total preview; validation near relevant fields; confirmation messages; clear empty states; status pills; keyboard-friendly native controls; responsive layout.
- **Error prevention:** non-negative quantities/prices; stock maximums; required order fields; duplicate SKU prevention; order quantity checked against stock on the server; discount capped by subtotal.
- **Recognition over recall:** visible product names/SKUs, searchable tables, status labels, contextual page headings, and help guidance.
- **Visibility of system status:** success/error alerts, current stock, pending/preparing/completed states, and order summary.
- **Consistency and standards:** shared page layout, navigation, button styles, and repeated form/table patterns.
- **System integrity:** SQLite relational tables for users, products, orders, order_items, and receipts; foreign keys connect transaction records.
- **Maintainability:** route handlers, templates, and stylesheet are separated.
- **Responsive access:** layout adapts to desktop, tablet, and mobile widths.

## 5. Main data model
- `users(id, username, password, role, display_name)`
- `products(id, name, sku, unit_price, stock, active)`
- `orders(id, customer, store, delivery_date, status, subtotal, discount, total, created_at)`
- `order_items(id, order_id, product_id, product_name, quantity, unit_price, line_total)`
- `receipts(id, order_id, receipt_number, issued_at)`

## 6. Core process flow
1. Authorized cashier/admin signs in.
2. User opens New Transaction and enters customer, store, delivery date, and quantities.
3. Browser previews line totals and grand total.
4. Server validates fields, stock, and discount.
5. System stores order and line items, deducts stock, and generates a receipt number in one database transaction.
6. Receipt page shows saved transaction details and print action.
7. Warehouse/admin uses the checklist and changes status from Pending to Preparing to Completed.
8. Admin reviews summary reports.

## 7. Scope and limitations
The uploaded study delimits the system to staff-entered orders and Mavailine Marketing's operational/order-fulfillment processes. It excludes payment gateway processing, a customer-facing e-commerce storefront, full ERP, GPS fleet tracking, and full offline synchronization. This prototype also does not ingest SMS messages automatically, does not provide genuine multi-device cloud synchronization, and does not send print jobs directly to a thermal printer. It uses local SQLite and the browser's print dialog.

## 8. Deployment/security work required before production
This is a teaching prototype, not a production-ready cloud service. Replace demo plaintext passwords with a strong password hash (e.g. Argon2id), set a secure random `SECRET_KEY` through environment variables, add CSRF protection, rate limiting, audit logs, database backups, HTTPS, role/permission tests, and a hosted database. Add transaction-safe stock updates and concurrency testing for multiple cashiers before real use.
