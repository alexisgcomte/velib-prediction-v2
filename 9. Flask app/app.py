from flask import Flask, render_template, request
app = Flask(__name__)
app = Flask(__name__,static_url_path='/static')

@app.route('/')
def home():
   return render_template('home.html')

@app.route('/result',methods = ['POST', 'GET'])
def result():
   if request.method == 'POST':
      result = request.form
      return render_template("result.html",result = result, imgname= "images/Capture.PNG")

@app.route('/prediction')
def prediction():
    return render_template('prediction.html')

@app.route('/about', methods=['GET', 'POST'])
def about():
    return render_template('about.html')

if __name__ == '__main__':
    app.run(debug=True)
