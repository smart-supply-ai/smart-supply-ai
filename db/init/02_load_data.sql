-- =============================================================================
-- 02_load_data.sql
-- Loads DataCoSupplyChainDataset.csv into supply_chain_data.
-- =============================================================================

COPY supply_chain_data (
    -- CSV column name                    → SQL column name
    type,                                 -- Type
    days_for_shipping_real,               -- Days for shipping (real)
    days_for_shipping_scheduled,          -- Days for shipment (scheduled)
    benefit_per_order,                    -- Benefit per order
    sales_per_customer,                   -- Sales per customer
    delivery_status,                      -- Delivery Status
    late_delivery_risk,                   -- Late_delivery_risk
    category_id,                          -- Category Id
    category_name,                        -- Category Name
    customer_city,                        -- Customer City
    customer_country,                     -- Customer Country
    customer_email,                       -- Customer Email
    customer_f_name,                      -- Customer Fname
    customer_id,                          -- Customer Id
    customer_l_name,                      -- Customer Lname
    customer_password,                    -- Customer Password
    customer_segment,                     -- Customer Segment
    customer_state,                       -- Customer State
    customer_street,                      -- Customer Street
    customer_zipcode,                     -- Customer Zipcode
    department_id,                        -- Department Id
    department_name,                      -- Department Name
    latitude,                             -- Latitude
    longitude,                            -- Longitude
    market,                               -- Market
    order_city,                           -- Order City
    order_country,                        -- Order Country
    order_customer_id,                    -- Order Customer Id
    order_date,                           -- order date (DateOrders)
    order_id,                             -- Order Id
    order_item_cardprod_id,               -- Order Item Cardprod Id
    order_item_discount,                  -- Order Item Discount
    order_item_discount_rate,             -- Order Item Discount Rate
    order_item_id,                        -- Order Item Id
    order_item_product_price,             -- Order Item Product Price
    order_item_profit_ratio,              -- Order Item Profit Ratio
    order_item_quantity,                  -- Order Item Quantity
    sales,                                -- Sales
    order_item_total,                     -- Order Item Total
    order_profit_per_order,               -- Order Profit Per Order
    order_region,                         -- Order Region
    order_state,                          -- Order State
    order_status,                         -- Order Status
    order_zipcode,                        -- Order Zipcode
    product_card_id,                      -- Product Card Id
    product_category_id,                  -- Product Category Id
    product_description,                  -- Product Description
    product_image,                        -- Product Image
    product_name,                         -- Product Name
    product_price,                        -- Product Price
    product_status,                       -- Product Status
    shipping_date,                        -- shipping date (DateOrders)
    shipping_mode                         -- Shipping Mode
)
FROM '/tmp/data/DataCoSupplyChainDataset.csv'
WITH (
    FORMAT    csv,
    HEADER    true,
    DELIMITER ',',
    ENCODING  'LATIN1',
    NULL      ''
);