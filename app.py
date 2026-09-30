from flask import Flask, render_template, request

app = Flask(__name__)

@app.route("/order", methods=["GET", "POST"])
def order():
    if request.method == "POST":
        print(request.form.get("flocked"))
        return "Thanks! We got your Order."
    return render_template("order.html")

if __name__ == "__main__":
    app.run(debug=True)