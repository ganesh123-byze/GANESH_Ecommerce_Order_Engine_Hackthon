from controllers.cli import CLIController

MENU = {
    '1': ('Add Product', 'add_product'),
    '2': ('View Products', 'view_products'),
    '3': ('Add to Cart', 'add_to_cart'),
    '4': ('Remove from Cart', 'remove_from_cart'),
    '5': ('View Cart', 'view_cart'),
    '6': ('Apply Coupon (noop)', 'apply_coupon'),
    '7': ('Place Order', 'place_order'),
    '8': ('Cancel Order', 'cancel_order'),
    '9': ('View Orders', 'view_orders'),
    '10': ('Low Stock Alert', 'low_stock_alert'),
    '11': ('Return Product', 'return_product'),
    '12': ('Simulate Concurrent Users', 'simulate_concurrent'),
    '13': ('View Logs', 'view_logs'),
    '14': ('Trigger Failure Mode', 'trigger_failure_mode'),
    '0': ('Exit', None)
}


def main():
    # ensure fraud service is initialized for CLI runs as well
    try:
        from services.fraud_service import init_fraud_service
        init_fraud_service()
    except Exception:
        pass
    cli = CLIController()
    while True:
        print("\n--- E-Commerce CLI ---")
        for k, v in MENU.items():
            print(k + ". " + v[0])
        choice = input("Choose: ")
        if choice not in MENU:
            print("Invalid")
            continue
        if choice == '0':
            break
        func_name = MENU[choice][1]
        func = getattr(cli, func_name)
        try:
            func()
        except Exception as e:
            print(f"Error: {e}")


if __name__ == '__main__':
    main()
