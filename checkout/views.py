from django.shortcuts import render, redirect, reverse, get_object_or_404
from django.contrib import messages
from django.conf import settings

from .forms import OrderForm
from .models import Order, OrderLineItem
from artwork.models import Artwork
from cart.contexts import cart_content


import stripe 

# Create your views here.

def checkout(request):
    stripe_public_key = settings.STRIPE_PUBLIC_KEY
    stripe_secret_key = settings.STRIPE_SECRET_KEY

    if request.method == "POST":
        cart = request.session.get('cart', {})

        form_data = {
            "full_name": request.POST["full_name"],
            "email": request.POST["email"],
            "phone_number": request.POST["phone_number"],
            "country": request.POST["country"],
            "town_or_city": request.POST["town_or_city"],
            "postcode": request.POST["postcode"],
            "street_address1": request.POST["street_address1"],
            "street_address2": request.POST["street_address2"],
        }

        order_form = OrderForm(form_data)
        
        if order_form.is_valid():
            order = order_form.save()
            for item_id, item_data in cart.items():
                try:
                    artwork = Artwork.objects.get(id=item_id)
                    if isinstance(item_data, int):
                        order_line_item = OrderLineItem(
                            order=order,
                            artwork=artwork,
                            quantity=item_data,
                        )
                        order_line_item.save()
                except Artwork.DoesNotExist:
                    messages.error(request, (
                        "One of your products in the bag cannot be found. Call us for assistance!"
                    ))
                    order.delete()
                    return redirect(reverse("view_cart"))

            request.session["save_info"] = "save-info" in request.POST
            return redirect(reverse("checkout_success", args=[order.order_number]))
        else:
            messages.error(request, "there was an error with the form. Please check your inputs.")
    else:
        cart = request.session.get('cart', {})
        if not cart:
            messages.error(request, "There are no items in your cart")
            return redirect(reverse('artwork'))

        current_cart = cart_content(request)
        total = current_cart["grand_total"]
        stripe_total = round(total*100)
        stripe.api_key = stripe_secret_key
        intent = stripe.PaymentIntent.create(
            amount=stripe_total,
            currency=settings.STRIPE_CURRENCY,
            )

        order_form = OrderForm()

    template = 'checkout/checkout.html'
    context = {
        'order_form': order_form,
        'stripe_public_key': stripe_public_key,
        'client_secret': intent.client_secret,
    }

    return render(request, template, context)


def checkout_success(request, order_number):
    save_info = request.session.get("save_info")
    order = get_object_or_404(Order, order_number=order_number)
    messages.success(request, f"Order successfully processed \
        your order number is the following {order_number} \
        a confirmation will be sent to {order.mail},")

    if "cart" in  request.session:
        del request.session["cart"] 

    template = "checkout/checkout_success.html"
    context = {
        order: order,
    }

    return render(request, template, context)