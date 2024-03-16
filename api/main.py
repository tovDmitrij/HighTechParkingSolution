from flask import Flask, request
app = Flask(__name__)
@app.route('/', methods=["POST"])
def process():
    print(request.json)
    return {"ok": True}
if __name__ == '__main__':
    app.run()