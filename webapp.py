from flask import Flask, redirect, url_for, session, request, jsonify, render_template, flash
from markupsafe import Markup
#from flask_apscheduler import APScheduler
#from apscheduler.schedulers.background import BackgroundScheduler
from flask_oauthlib.client import OAuth
from bson.objectid import ObjectId

import pprint
import os
import time
import pymongo
import sys
import json
from flask import Flask, url_for, render_template, request
from flask import redirect
from flask import session
 
 
app = Flask(__name__)

app.debug = False #Change this to False for production
#os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1' #Remove once done debugging

app.secret_key = os.environ['SECRET_KEY'] #used to sign session cookies
oauth = OAuth(app)
oauth.init_app(app) #initialize the app to be able to make requests for user information

#Set up GitHub as OAuth provider
github = oauth.remote_app(
    'github',
    consumer_key=os.environ['GITHUB_CLIENT_ID'], #your web app's "username" for github's OAuth
    consumer_secret=os.environ['GITHUB_CLIENT_SECRET'],#your web app's "password" for github's OAuth
    request_token_params={'scope': 'user:email'}, #request read-only access to the user's email.  For a list of possible scopes, see developer.github.com/apps/building-oauth-apps/scopes-for-oauth-apps
    base_url='https://api.github.com/',
    request_token_url=None,
    access_token_method='POST',
    access_token_url='https://github.com/login/oauth/access_token',  
    authorize_url='https://github.com/login/oauth/authorize' #URL for github's OAuth login
)

#Connect to database
url = os.environ["MONGO_CONNECTION_STRING"]
client = pymongo.MongoClient(url)
db = client[os.environ["MONGO_DBNAME"]]
collection = db['Food'] #TODO: put the name of the collection here

# Send a ping to confirm a successful connection
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)




#context processors run before templates are rendered and add variable(s) to the template's context
#context processors must return a dictionary 
#this context processor adds the variable logged_in to the conext for all templates
@app.context_processor
def inject_logged_in():
    return {"logged_in":('github_token' in session)}

@app.route('/')
def home():
    return render_template('home.html')

#redirect to GitHub's OAuth page and confirm callback URL
@app.route('/login')
def login():   
    return github.authorize(callback=url_for('authorized', _external=True, _scheme='https')) #callback URL must match the pre-configured callback URL

@app.route('/logout')
def logout():
    session.clear()
    flash('You were logged out.')
    return redirect('/')

@app.route('/login/authorized')
def authorized():
    resp = github.authorized_response()
    if resp is None:
        session.clear()
        flash('Access denied: reason=' + request.args['error'] + ' error=' + request.args['error_description'] + ' full=' + pprint.pformat(request.args), 'error')      
    else:
        try:
            session['github_token'] = (resp['access_token'], '') #save the token to prove that the user logged in
            session['user_data']=github.get('user').data
            #pprint.pprint(vars(github['/email']))
            #pprint.pprint(vars(github['api/2/accounts/profile/']))
            flash('You were successfully logged in as ' + session['user_data']['login'] + '.')
        except Exception as inst:
            session.clear()
            print(inst)
            flash('Unable to login, please try again.', 'error')
    return redirect('/')


@app.route('/page1', methods=['GET','POST'])
def renderPage1():
    macro_Info = ""
    descriptions = ""
    sugar_Info = ""
    fat_Info = ""
    carb_Info = ""
    macros = 0
    sugar = 0
    fat = 0
    carb = 0
    if "search" in request.args:
        category = request.args.get('search').lower().capitalize()
        descriptions = get_description_options(category)
    elif "description" in request.args:
        description = request.args.get('description')
        macros = get_data(description, "Protein")
        sugar = get_data(description, "Sugar Total")
        fat = get_fat_data(description)
        carb = get_data(description, "Carbohydrate")
        macro_Info = "Protein: " + str(macros) + " grams per serving"
        sugar_Info = "Total Sugar: " + str(sugar) + " grams per serving"
        fat_Info = "Saturated Fat: " + str(fat) + " grams per serving"
        carb_Info = "Carbs: " + str(carb) + " grams per serving"
    return render_template('page1.html', description_options=descriptions, macroInfo=macro_Info, sugarInfo=sugar_Info, fatInfo=fat_Info, carbInfo=carb_Info, macros=macros, sugar=sugar, fat=fat, carb=carb)
    

@app.route('/page2', methods=['GET','POST'])
def renderPage2():
	name = ""
	height = ""
	weight = ""
	age = ""
	weight_goal = None
	doc = None
	if 'user_data' in session:
		doc = collection.find_one({'id': session['user_data']['login']})

	if request.method == 'POST':
		session["name"] = request.form.get('name')
		session["height"] = request.form.get('height')
		session["weight"] = request.form.get('weight')
		session["age"] = request.form.get('age')
		session["weight_goal"] = request.form.get('age')
		name = request.form.get('name')
		height = request.form.get('height')
		weight = request.form.get('weight')
		age = request.form.get('age')
		weight_goal = request.form.get('weight_goal')
		user_info = {
			"id": session['user_data']['login'],
			"name": name,
			"height": height,
			"weight": weight,				
			"age": age,
			"weight_goal": weight_goal
		}
		test1 = collection.find_one_and_update(
			{'id': session['user_data']['login']},
			{'$set': {
				'name': name,
				'weight': weight,
				'height': height,
				'age': age,
				'weight_goal': weight_goal
			}})
		# 	test1 = collection.insert_one(user_info) 
		doc = collection.find_one({'id': session['user_data']['login']})
		print(doc)
		if doc == None:
			collection.insert_one(user_info)
		else: 
			collection.find_one_and_update({'id' : session['user_data']['login']}, {'$set': {'name' : name}, '$set': {'weight': weight}, '$set': {'height': height}, '$set': {'age': age}, '$set': {'weight_goal':weight_goal}})
		doc2 = collection.find_one({'id': session['user_data']['login']})
		return render_template('page2.html', doc=doc2)
	return render_template('page2.html', doc=doc)




@app.route('/page3', methods=['GET','POST'])
def renderPage3():
	macros_total = 0
	sugar = 0
	fat = 0
	carb = 0
	gainWeight = ""
	gainFat = ""
	gainCarb = ""
	gainSugar = ""
	search_value = "Search... "
	
	doc = None	
	if "clear" in request.args:
		test1 = collection.find_one_and_update(
			{'id': session['user_data']['login']},
			{'$set': {
				"protein": 0,
				"sugar": 0,
				"fat": 0,				
				"carb": 0,
			}})
	if 'user_data' in session:
		doc = collection.find_one({'id': session['user_data']['login']})
	descriptions = ""
	if "search" in request.args or "description" in request.args:
		search_value = request.args.get('search')
		if search_value:
			category = search_value.lower().capitalize()
			descriptions = get_description_options(category)
		description = request.args.get('description')
		macros_total += get_data(description, "Protein")
		sugar += get_data(description, "Sugar Total")
		fat += get_fat_data(description)
		carb += get_data(description, "Carbohydrate")
		user_info = {
			"id": session['user_data']['login'],
			"protein": macros_total,
			"sugar": sugar,
			"fat": fat,				
			"carb": carb,
		}
		print(user_info)
		test1 = collection.find_one_and_update(
			{'id': session['user_data']['login']},
			{'$inc': {
				"protein": macros_total,
				"sugar": sugar,
				"fat": fat,				
				"carb": carb,
			}})
		print(test1)
	doc = collection.find_one({'id': session['user_data']['login']})
	
	if doc == None:
		collection.insert_one(user_info)
	else: 
		collection.find_one_and_update({'id' : session['user_data']['login']}, {'$inc': {'protein' : macros_total}, '$inc': {'sugar': sugar}, '$inc': {'fat': fat}, '$inc': {'carb': carb}})
	doc2 = collection.find_one({'id': session['user_data']['login']})
	
	
	weight = float(doc['weight'])
	protein = float(doc['protein'])
	fats = float(doc['fat'])
	carbs = float(doc['carb'])
	sugars = float(doc['sugar'])
	if 0.36 * weight > protein:
		if doc['weight_goal'] == "Gain":
			gainWeight = "You\'re protein consumption is below the daily recommended. You said you wanted to gain weight so you need to eat more!"
		else: 
			gainWeight = "You\'re protein consumption is below the daily recommended. You said you wanted to lose weight so you are on the right track!"
	else:
		if doc['weight_goal'] == "Gain":
			gainWeight = "You\'re protein consumption is above the daily recommended. You said you wanted to gain weight so you are on the right track!"
		else: 
			gainWeight = "You\'re protein consumption is above the daily recommended. You said you wanted to lose weight so you need to eat more!"
	if 0.7 * weight > fats:
		if doc['weight_goal'] == "Gain":
			gainFat = "You\'re fat consumption is below the daily recommended. You said you wanted to gain weight so you need to eat more!"
		else: 
			gainFat = "You\'re fat consumption is below the daily recommended. You said you wanted to lose weight so you are on the right track!"
	else:
		if doc['weight_goal'] == "Gain":
			gainFat = "You\'re fat consumption is above the daily recommended. You said you wanted to gain weight so you are on the right track!"
		else: 
			gainFat = "You\'re fat consumption is above the daily recommended. You said you wanted to lose weight so you need to eat more!"
	if 1 * weight > carbs:
		if doc['weight_goal'] == "Gain":
			gainCarb = "You\'re carb consumption is below the daily recommended. You said you wanted to gain weight so you need to eat more!"
		else: 
			gainCarb = "You\'re carb consumption is below the daily recommended. You said you wanted to lose weight so you are on the right track!"
	else:
		if doc['weight_goal'] == "Gain":
			gainCarb = "You\'re carb consumption is above the daily recommended. You said you wanted to gain weight so you are on the right track!"
		else: 
			gainCarb = "You\'re carb consumption is above the daily recommended. You said you wanted to lose weight so you need to eat more!"
	if 0.2 * weight > sugars:
		if doc['weight_goal'] == "Gain":
			gainSugar = "You\'re sugar consumption is below the daily recommended. You said you wanted to gain weight so you need to eat more!"
		else: 
			gainSugar = "You\'re sugar consumption is below the daily recommended. You said you wanted to lose weight so you are on the right track!"
	else:
		if doc['weight_goal'] == "Gain":
			gainSugar = "You\'re sugar consumption is above the daily recommended. You said you wanted to gain weight so you are on the right track!"
		else: 
			gainSugar = "You\'re sugar consumption is above the daily recommended. You said you wanted to lose weight so you need to eat more!"
	
	if search_value == None:
		search_value = "Search... "
	return render_template('page3.html', doc=doc2, description_options=descriptions, macros=macros_total, sugar=sugar, fat=fat, carb=carb, gainWeight=gainWeight, gainFat=gainFat, gainCarb=gainCarb, gainSugar=gainSugar, search_value=search_value)
# 	return render_template('page3.html', doc=doc, description_options=descriptions, macros=macros_total, sugar=sugar, fat=fat, carb=carb, gainWeight=gainWeight, gainFat=gainFat, gainCarb=gainCarb, gainSugar=gainSugar)
    
    
    
@app.route('/page4')
def renderPage4():


	return render_template('page4.html')

def get_data(description, dataType):
    with open('food.json') as food_data:
        foods = json.load(food_data)
    data = 0
    for c in foods:
        if c["Description"] == description:
            data = c["Data"][dataType]
    return data
    
    
def get_description_options(category):
    """Return the html code for the drop down menu.  Each option is a state abbreviation from the demographic data."""
    with open('food.json') as food_data:
        allFoods = json.load(food_data)
    foods=[]
    for c in allFoods:
        if c["Category"] == category:
            if c["Description"] not in foods:
                foods.append(c["Description"])
    options=""
    for s in foods:
        options += Markup("<option value=\"" + s + "\">" + s + "</option>") #Use Markup so <, >, " are not escaped lt, gt, etc.
    return options


    
def get_fat_data(description):
    with open('food.json') as food_data:
        foods = json.load(food_data)
    data = 0
    for c in foods:
        if c["Description"] == description:
            data = c["Data"]["Fat"]["Saturated Fat"]
    return data


#the tokengetter is automatically called to check who is logged in.
@github.tokengetter
def get_github_oauth_token():
    return session['github_token']


if __name__ == '__main__':
    app.run(debug=True)
