from flask import Flask, render_template, request

app = Flask(__name__)

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
            print(order_data)
            return "Thanks! We got your Order."
    return render_template("order.html")

if __name__ == "__main__":
    app.run(debug=True)