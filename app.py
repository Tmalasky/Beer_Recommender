from flask import Flask, render_template, request, redirect, url_for
import beer_model_script

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def home():       
    return render_template("Beer_Recommender.html")


@app.route("/your-beers", methods=["GET", "POST"])
def your_beers():
    if request.method == "POST":
        user_input = request.form.getlist('user_input')
        pred_style, top_5_same_style, top_5_diff_style = beer_model_script.find_beers(user_input)
        return render_template(
            "your-beers.html", pred_style = pred_style, top_5_same_style = top_5_same_style, top_5_diff_style = top_5_diff_style
            )
    else:
        return render_template(
            "your-beers.html", pred_style = pred_style, top_5_same_style = top_5_same_style, top_5_diff_style = top_5_diff_style
            )


if __name__ == "__main__":
    app.run(debug=True)