from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_mysqldb import MySQL
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)

mysql = MySQL(app)
# Configurações do MySQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'i-equus'
app.config['MYSQL_DB'] = 'equusDB'

# Folder where the pictures will be saved
UPLOAD_FOLDER = 'static/horses_pictures/'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


#horses list
@app.route('/horses')
def get_horses():
    cursor = mysql.connection.cursor()
    cursor.execute('''SELECT * FROM horses''')
    horses = cursor.fetchall()
    cursor.close()
    
    return render_template('horses.html', horses=horses)



@app.route('/add_horse', methods=['GET', 'POST'])
def add_horse():
    if request.method == 'POST':
        # Get form data
        name = request.form['name']
        weight = request.form['weight']
        health_score = request.form['health_score']
        """
        # Handle picture upload
        if 'picture' not in request.files:
            return 'No file part'
        
        file = request.files['picture']
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            picture_name = filename
            date_taken = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Save the file to the uploads folder
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            
            cursor = mysql.connection.cursor()


            
            # Insert the picture information into the 'horse_pictures' table
            cursor.execute('''INSERT INTO horse_pictures (horse_id, picture_name, date_taken) 
                              VALUES (%s, %s, %s)''', (horse_id, picture_name, date_taken))
"""
            # Insert horse data into the 'horses' table
        cursor.execute('''INSERT INTO horses (name, weight, health_score) 
                            VALUES (%s, %s, %s)''', (name, weight, health_score))
        horse_id = cursor.lastrowid  # Get the ID of the newly inserted horse            

        # Commit the changes and close the cursor
        mysql.connection.commit()
        cursor.close()

        # Redirect to the list of horses
        return redirect(url_for('get_horses'))

    return render_template('add_horse.html')