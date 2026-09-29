from src.fintech_background import PaymentEvent, approve_listing


def test_payment_country_controls_publish_decision():
    accepted = PaymentEvent("sku-42", 1299, "US", b"x", "product.jpg")
    review = PaymentEvent("sku-42", 1299, "DE", b"x", "product.jpg")
    assert approve_listing(accepted) is True
    assert approve_listing(review) is False
