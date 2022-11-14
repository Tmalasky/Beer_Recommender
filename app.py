from flask import Flask, render_template, redirect, url_for
import beer_model_script

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("Beer_Recommender.html")


@app.route("/your-beers")
def beers():
    pred_style, top_5_same_style, top_5_diff_style = beer_model_script.find_beers()
    return render_template("your-beers.html", pred_style = pred_style, top_5_same_style = top_5_same_style, top_5_diff_style = top_5_diff_style)


if __name__ == "__main__":
    app.run(debug=True)