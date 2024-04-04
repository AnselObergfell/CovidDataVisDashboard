import dash
from dash import dcc, html, Input, Output
import plotly.express as px
import pandas as pd

df = pd.read_csv('COVID-19_Vaccinations_in_the_US.csv')
locations_to_drop = ['DD2', 'BP2', 'GU', 'MH', 'MP', 'PW', 'PR', 'LTC', 'VI', 'RP', 'IH2', 'FM', 'AS', 'DC', 'US']
df = df[~df['Location'].isin(locations_to_drop)]
app = dash.Dash(__name__)
server = app.server
states = sorted(df['Location'].unique())
colors = px.colors.sample_colorscale("Jet", [n/(len(states) -1) for n in range(len(states))])
color_dict = {state: color for state, color in zip(states, colors)}

min_week = df['MMWR_week'].min()
max_week = df['MMWR_week'].max()-1
week_range_values = df['MMWR_week'].unique()
week_range_index = list(range(len(week_range_values)))

app.layout = html.Div([
    html.H1("COVID-19 Vaccination Data Dashboard"),
    
    html.Div([
        dcc.Checklist(
            id='state-checklist',
            options=[{'label': [html.Span(state), html.Div(style={'display': 'inline-block', 'width': '10px', 'height': '10px', 'background-color': color_dict[state]})], 'value': state} for state in states],
            value=[states[0]],
            className='checklist'
        )
    ]),
    
    html.Div([
        dcc.RangeSlider(
            id='week-range-slider',
            min=min_week,
            max=max_week,
            value=[min_week, max_week],
            step=1
        )
    ]),
    
    html.Div([
        dcc.Graph(id='line-plot')
    ]),
    
    html.Div([
        dcc.Graph(id='shots-by-vendor-pie-chart')
    ]),
    html.Div([
        dcc.Graph(id='shots-administered-distributed-bar-chart')
    ]),
    html.Div([
        dcc.Graph(id='series-complete-pop-pct-map')
    ])
])

@app.callback(
    Output('line-plot', 'figure'),
    [Input('state-checklist', 'value'), Input('week-range-slider', 'value')]
)
def update_line_plot(selected_states, week_range_index):
    start_week = week_range_values[week_range_index[0]]
    end_week = week_range_values[week_range_index[1]]
    
    fig = px.line(title='Administered Doses Over Time')
    for state in selected_states:
        filtered_df = df[(df['Location'] == state) & df['MMWR_week'].between(start_week, end_week)]
        weekly_administered = filtered_df.groupby('MMWR_week')['Administered'].sum().reset_index()
        fig.add_trace(px.line(weekly_administered, x='MMWR_week', y='Administered', title=state, color_discrete_sequence=[color_dict[state]]).data[0])
    
    return fig

@app.callback(
    Output('shots-by-vendor-pie-chart', 'figure'),
    [Input('state-checklist', 'value'), Input('week-range-slider', 'value')]
)
def update_pie_chart(selected_states, week_range_index):
    start_week = week_range_values[week_range_index[0]]
    end_week = week_range_values[week_range_index[1]]

    filtered_df = df[df['Location'].isin(selected_states) & df['MMWR_week'].between(start_week, end_week)]
    vendor_shots = filtered_df[['Administered_Janssen', 'Administered_Moderna', 'Administered_Pfizer', 'Administered_Novavax']].sum()
    total_shots = vendor_shots.sum()
    vendor_shots_percentage = (vendor_shots / total_shots) * 100
    fig = px.pie(names=vendor_shots_percentage.index, values=vendor_shots_percentage.values,
                 title='Percentage of Shots by Vendor')
    return fig

@app.callback(
    Output('shots-administered-distributed-bar-chart', 'figure'),
    [Input('state-checklist', 'value'), Input('week-range-slider', 'value')]
)
def update_bar_chart(selected_states, week_range_index):
    start_week = week_range_values[week_range_index[0]]
    end_week = week_range_values[week_range_index[1]]
    
    filtered_df = df[df['Location'].isin(selected_states) & df['MMWR_week'].between(start_week, end_week)]
    
    state_totals = filtered_df.groupby('Location').agg({'Administered': 'sum', 'Distributed': 'sum'}).reset_index()
    
    state_totals['Administered_Percentage'] = (state_totals['Administered'] / (state_totals['Administered'] + state_totals['Distributed'])) * 100
    state_totals['Distributed_Percentage'] = (state_totals['Distributed'] / (state_totals['Administered'] + state_totals['Distributed'])) * 100
    
    state_totals_melted = pd.melt(state_totals, id_vars=['Location'], value_vars=['Administered_Percentage', 'Distributed_Percentage'],
                                   var_name='Dose Type', value_name='Percentage')
    fig = px.bar(state_totals_melted, x='Location', y='Percentage', color='Dose Type',
                 title='Percentage of Shots Administered vs Distributed by State', barmode='stack')
    
    return fig
@app.callback(
    Output('series-complete-pop-pct-map', 'figure'),
    [Input('week-range-slider', 'value')]
)
def update_map(week_range_index):
    # Convert MMWR week range index to MMWR week values
    start_week = week_range_values[week_range_index[0]]
    end_week = week_range_values[week_range_index[1]]
    
    # Filter data for selected time range
    filtered_df = df[df['MMWR_week'].between(start_week, end_week)]
    
    # Get maximum Series_Complete_Pop_Pct for each state
    max_series_complete_pop_pct = filtered_df.groupby('Location')['Series_Complete_Pop_Pct'].max().reset_index()
    
    # Create choropleth map
    fig = px.choropleth(max_series_complete_pop_pct, locations='Location', locationmode='USA-states',
                        color='Series_Complete_Pop_Pct', hover_data=['Location', 'Series_Complete_Pop_Pct'],
                        scope='usa', title='Maximum Series Complete Population Percentage')
    
    fig.update_layout(mapbox_style="carto-positron", mapbox_zoom=3, mapbox_center = {"lat": 37.0902, "lon": -95.7129})
    
    return fig
if __name__ == '__main__':
    app.run_server(debug=True)
