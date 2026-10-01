from flask import Flask, render_template, request

app = Flask(__name__)

REQUIRED_FIELDS = {
    "species": "a tree type",
    "tree_size": "a tree size",
    "name": "your name",
    "phone": "your phone number",
    "street": "your street address",
    "city": "your city",
    "delivery_date": "a delivery date",
    "time_window": "a delivery time",
    "payment": "a payment method",
}


def validate_order(data):
    errors = []

    for field, label in REQUIRED_FIELDS.items():
        if data[field] == "":
            errors.append(f"Please enter {label}.")

    if data["quantity"] is None or not 1 <= data["quantity"] <= 50:
        errors.append("Please enter a quantity between 1 and 50.")

    return errors


@app.route("/order", methods=["GET", "POST"])
def order():
    if request.method == "POST":
            order_data = {
                "species": request.form.get("species", "").strip(),
                "tree_size": request.form.get("tree_size", "").strip(),
                "flocked": request.form.get("flocked") == "yes",
                "name": request.form.get("name", "").strip(),
                "email": request.form.get("email", "").strip(),
                "phone": request.form.get("phone", "").strip(),
                "street": request.form.get("street", "").strip(),
                "apt": request.form.get("apt", "").strip(),
                "city": request.form.get("city", "").strip(),
                "zip": request.form.get("zip", "").strip(),
                "delivery_date": request.form.get("delivery_date", "").strip(),
                "time_window": request.form.get("time_window", "").strip(),
                "delivery_notes": request.form.get("delivery_notes", "").strip(),
                "payment": request.form.get("payment", "").strip(),
            }
            
            try:
                order_data["quantity"] = int(request.form.get("quantity",""))
            except ValueError:
                order_data["quantity"] = None
            errors = validate_order(order_data)
            if errors:
                return render_template("order.html", errors=errors)

            print(order_data)
            return "Thanks! We got your Order."

    return render_template("order.html")

if __name__ == "__main__":
    app.run(debug=True)