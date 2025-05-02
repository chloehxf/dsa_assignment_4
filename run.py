from flaskapp import app

if __name__ == '__main__':
    app.run(debug=True, port=5005)

# configuring the SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'

# SQLAlchemy database instance
db = SQLAlchemy(app)
app.app_context().push()