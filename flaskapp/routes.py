from flask import render_template, flash, redirect, url_for, request
from flaskapp import app, db
from flaskapp.models import BlogPost, IpView, Day, UkData
from flaskapp.forms import PostForm
import datetime
import statsmodels

import pandas as pd
import json
import plotly
import plotly.express as px


# Route for the home page, which is where the blog posts will be shown
@app.route("/")
@app.route("/home")
def home():
    # Querying all blog posts from the database
    posts = BlogPost.query.all()
    return render_template('home.html', posts=posts)


# Route for the about page
@app.route("/about")
def about():
    return render_template('about.html', title='About page')


# Route to where users add posts (needs to accept get and post requests)
@app.route("/post/new", methods=['GET', 'POST'])
def new_post():
    form = PostForm()
    if form.validate_on_submit():
        post = BlogPost(title=form.title.data, content=form.content.data, user_id=1)
        db.session.add(post)
        db.session.commit()
        flash('Your post has been created!', 'success')
        return redirect(url_for('home'))
    return render_template('create_post.html', title='New Post', form=form)


# • Who are you displaying this data for?
# • What do they want out of it?
# • What is important for them to understand?
# • What are they using it for?

# Route to UK chart
@app.route('/uk')
def uk():
    uk = UkData.query.all()
    data = pd.DataFrame([{
        'TotalVote': row.TotalVote19,
        'BrexitVote': row.BrexitVote19,
        'Region': row.region}
        for row in uk])

    # Aggregate the data by Region
    aggregated_data = data.groupby('Region').agg({
        'TotalVote': 'sum',  # Sum of TotalVote per Region
        'BrexitVote': 'sum'  # Sum of BrexitVote per Region
    }).reset_index()

    # Calculate the percentage of BrexitVote relative to TotalVote
    aggregated_data['BrexitVotePercentage'] = (aggregated_data['BrexitVote'] / aggregated_data['TotalVote']) * 100
    aggregated_data['TotalVotePercentage'] = 100 - aggregated_data['BrexitVotePercentage']

    # Reshape the data to long format for the stacked bar chart
    df_long = aggregated_data.melt(id_vars=["Region"], value_vars=["BrexitVotePercentage", "TotalVotePercentage"], 
                                var_name="Metric", value_name="Percentage")

    # Specify colors for the bar chart
    legend_color = {
        'BrexitVotePercentage': 'darkblue',
        'TotalVotePercentage': 'lightgray'
    }

    # Create bar chart
    fig = px.bar(df_long, x='Region', y='Percentage', color='Metric', 
                title='Percentage Brexit Vote per Region', 
                labels={'Percentage': 'Percentage of Brexit Vote (%)', 'Region': 'Region', 'Metric': 'Vote Type'},
                barmode='stack', color_discrete_map=legend_color)


    fig.show()
    # Convert to JSON to render to Flask
    graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    return render_template('uk.html', title='Percentage of Brexit Vote per UK Region (2019)', graphJSON=graphJSON)

@app.route('/uk2')
def uk2():
    uk = UkData.query.all()
    df = pd.DataFrame([{
        'Constituency': row.constituency_name,
        'BrexitVote19': row.BrexitVote19,
        'c11Female': row.c11Female,
        'c11HouseholdMarried': row.c11HouseholdMarried,
        'c11HouseOwned': row.c11HouseOwned,
        'c11Retired': row.c11Retired,
        'c11FulltimeStudent': row.c11FulltimeStudent
        } for row in uk])
    # fig = px.bar(df, x='Region', y='Turnout')
    # Initial scatter plot (BrexitVote19 vs c11Female)
    fig = px.scatter(df,
                 x='BrexitVote19',
                 y='c11Female',
                 hover_name='Constituency',
                 title='Demographics (2011) of the Brexit Vote (2019)',
                 labels={'BrexitVote19': 'Brexit Vote', 'c11Female': 'Female (%)'})

    # Create dropdown buttons for other y-axis options
    y_vars = {
        'c11Female': 'Female (%)',
        'c11HouseholdMarried': 'Married Households (%)',
        'c11HouseOwned': 'House Owned (%)',
        'c11Retired': 'Retired (%)',
        'c11FulltimeStudent': 'Full-time Students (%)'
    }

    dropdown_buttons = [
    {
        'label': label,
        'method': 'update',
        'args': [
            {'y': [df[col]]},
            {'yaxis': {'title': label}}  # Set axis label and fixed range
        ]
    }
    for col, label in y_vars.items()
]

    fig.update_layout(
        updatemenus=[{
            'type': 'buttons',
            'buttons': dropdown_buttons,
            'direction': 'down',
            'showactive': True,
            'xanchor': 'right'
        }]
    )
    # Set aesthetics of chart
    fig.update_traces(marker=dict(size=10, color='orange', opacity=0.6))
    graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    return render_template('uk.html', title='Demographics (2011) of the Brexit Vote (2019)', graphJSON=graphJSON)


# Route to the dashboard page
@app.route('/dashboard')
def dashboard():
    days = Day.query.all()
    df = pd.DataFrame([{'Date': day.id, 'Page views': day.views} for day in days])

    fig = px.bar(df, x='Date', y='Page views')

    graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    return render_template('dashboard.html', title='Page views per day', graphJSON=graphJSON)


@app.before_request
def before_request_func():
    day_id = datetime.date.today()  # get our day_id
    client_ip = request.remote_addr  # get the ip address of where the client request came from

    query = Day.query.filter_by(id=day_id)  # try to get the row associated to the current day
    if query.count() > 0:
        # the current day is already in table, simply increment its views
        current_day = query.first()
        current_day.views += 1
    else:
        # the current day does not exist, it's the first view for the day.
        current_day = Day(id=day_id, views=1)
        db.session.add(current_day)  # insert a new day into the day table

    query = IpView.query.filter_by(ip=client_ip, date_id=day_id)
    if query.count() == 0:  # check if it's the first time a viewer from this ip address is viewing the website
        ip_view = IpView(ip=client_ip, date_id=day_id)
        db.session.add(ip_view)  # insert into the ip_view table

    db.session.commit()  # commit all the changes to the database
