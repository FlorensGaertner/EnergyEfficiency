import random
import dash
import pandas as pd
from dash import Dash, dcc, html
import plotly.graph_objects as go
from dash.dependencies import Input, Output

# Load your data
data_file = '/mnt/data/energy_efficiency_data.csv'
df = pd.read_csv('energy_efficiency_data.csv')

# Calculate Total_Load and drop Heating_Load, Cooling_Load columns if they exist
if 'Heating_Load' in df.columns and 'Cooling_Load' in df.columns:
    df['Total_Load'] = df['Heating_Load'] + df['Cooling_Load']
    df_for_scatter = df.copy()  # Make a copy for scatter plot and table
    df_for_scatter.drop(['Heating_Load', 'Cooling_Load', 'Wall_Area', 'Roof_Area'], axis=1, inplace=True)
else:
    df_for_scatter = df.drop(['Wall_Area', 'Roof_Area'], axis=1)

# Calculate mean Total_Load per Relative_Compactness, Glazing_Area, and Overall_Height
mean_total_load_per_rc_ga = df_for_scatter.groupby(['Relative_Compactness', 'Glazing_Area', 'Overall_Height'])['Total_Load'].mean().reset_index()
mean_total_load_per_rc_ga['Total_Load'] = mean_total_load_per_rc_ga['Total_Load'].round(1)  # Round to 1 decimal place
mean_total_load_per_rc_ga['Total_Load'] = mean_total_load_per_rc_ga['Total_Load'].apply(lambda x: f'{x:.1f}' if x.is_integer() else f'{x}')

# Initialize the Dash app
app = Dash(__name__, assets_folder='C:\\Users\\flore\\OneDrive\\Desktop\\data_project\\assets')

# Define app layout with inline styles for larger width and flex display
app.layout = html.Div(
    style={'width': '90%', 'max-width': '1200px', 'margin': 'auto', 'height': '200vh'},  # Adjust width and max-width for larger dashboard
    children=[
        html.H1("Energy Efficiency Dashboard"),  # Header displayed at the top of the dashboard

        # Heatmap for correlation matrix
        html.Div([
            html.H2("Correlation Matrix of Energy Efficiency Factors"),
            dcc.Graph(
                id='correlation-heatmap',
                figure={}  # Placeholder for now
            )
        ]),

        html.Hr(),

        # Image buttons to select Relative_Compactness
        html.Div(
            id='compactness-images',
            children=[
                html.Img(src=f'/assets/Relative-Compactness-{str(val).replace(".", "_")}.png',
                         id=f'compactness-{str(val).replace(".", "_")}',
                         style={'width': 'auto', 'height': '100px', 'margin-right': '10px', 'cursor': 'pointer'})
                for val in sorted(df['Relative_Compactness'].unique(), reverse=True)  # Sort in descending order
            ],
            style={'display': 'flex', 'flex-wrap': 'wrap', 'justify-content': 'center'}
        ),

        # Hidden div to store the selected Relative_Compactness
        dcc.Store(id='selected-compactness', data=str(sorted(df['Relative_Compactness'].unique())[0]).replace(".", "_")),

        # Message for no data
        html.Div(id='no-data-message', style={'color': 'red', 'font-size': '20px', 'margin-top': '10px'}),

        # Combined Graph for Total_Load vs Glazing_Area with height of 3.5 and 7
        html.Div([
            html.H2("Total Load per Glazing Area by Room Height"),
            dcc.Graph(id='total-load-graph')
        ]),

        # Table to display mean Total_Load per Glazing_Area
        html.Div(id='mean-load-table'),

        # Display current room height text
        html.Div(id='current-room-height', style={'margin-top': '10px', 'font-size': '18px', 'text-align': 'center'})
    ]
)

# Define callback to update the selected Relative_Compactness
@app.callback(
    Output('selected-compactness', 'data'),
    [Input(f'compactness-{str(val).replace(".", "_")}', 'n_clicks') for val in sorted(df['Relative_Compactness'].unique())]
)
def update_selected_compactness(*args):
    ctx = dash.callback_context
    if not ctx.triggered:
        return str(sorted(df['Relative_Compactness'].unique())[0]).replace(".", "_")
    else:
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        return button_id.split('-')[1]

# Define callback to update graphs, table, and heatmap based on the selected Relative_Compactness
@app.callback(
    [Output('total-load-graph', 'figure'),
     Output('mean-load-table', 'children'),
     Output('correlation-heatmap', 'figure'),
     Output('no-data-message', 'children'),
     Output('current-room-height', 'children')],
    [Input('selected-compactness', 'data')]
)
def update_data(selected_compactness):
    selected_compactness = float(selected_compactness.replace("_", "."))

    # Filter data for the selected Relative_Compactness for scatter plot and table
    filtered_df_3_5 = mean_total_load_per_rc_ga[(mean_total_load_per_rc_ga['Relative_Compactness'] == selected_compactness) &
                                                (mean_total_load_per_rc_ga['Overall_Height'] == 3.5)]
    filtered_df_7 = mean_total_load_per_rc_ga[(mean_total_load_per_rc_ga['Relative_Compactness'] == selected_compactness) &
                                              (mean_total_load_per_rc_ga['Overall_Height'] == 7)]

    no_data_message = ""
    if filtered_df_3_5.empty:
        no_data_message += f'No data available for the room height of 3.5 for the relative compactness of {selected_compactness}. '
        current_height_text = f"Current Room Height: N/A"
    else:
        current_height_text = f"Current Room Height: {filtered_df_3_5['Overall_Height'].unique()[0]}"

    if filtered_df_7.empty:
        no_data_message += f'No data available for the room height of 7 for the relative compactness of {selected_compactness}.'

    combined_df = pd.concat([filtered_df_3_5, filtered_df_7])
    if combined_df.empty:
        fig = go.Figure().update_layout(title=f'NOTE: No data available for Relative Compactness: {selected_compactness}')
    else:
        fig = go.Figure()

        if not filtered_df_3_5.empty:
            # Use .loc to avoid SettingWithCopyWarning
            filtered_df_3_5.loc[:, 'Total_Load'] = pd.to_numeric(filtered_df_3_5['Total_Load'], errors='coerce')

            fig.add_trace(go.Bar(
                x=filtered_df_3_5['Glazing_Area'],
                y=filtered_df_3_5['Total_Load'],
                name='Room Height 3.5',
                marker_color='blue',  # Adjust color as needed
                text=[f'Glazing Area: {row.Glazing_Area}<br>Total Load: {row.Total_Load}' for i, row in filtered_df_3_5.iterrows()],
                hoverinfo='text'
            ))

        if not filtered_df_7.empty:
            # Use .loc to avoid SettingWithCopyWarning
            filtered_df_7.loc[:, 'Total_Load'] = pd.to_numeric(filtered_df_7['Total_Load'], errors='coerce')

            fig.add_trace(go.Bar(
                x=filtered_df_7['Glazing_Area'],
                y=filtered_df_7['Total_Load'],
                name='Room Height 7',
                marker_color='green',  # Adjust color as needed
                text=[f'Glazing Area: {row.Glazing_Area}<br>Total Load: {row.Total_Load}' for i, row in filtered_df_7.iterrows()],
                hoverinfo='text'
            ))

        fig.update_layout(
            barmode='group',  # Use 'stack' for stacked bars or 'group' for grouped bars
            title=f'Mean Total Load per Glazing Area ({selected_compactness})',
            xaxis_title='Glazing Area',
            yaxis_title='Total Load',
            yaxis=dict(range=[0, 100]),  # Fix the range of y-axis from 0 to 100
            legend_title_text='Room Height'
        )
        
    # Table with mean Total_Load per Glazing_Area
    table = html.Table([
        html.Thead(
            html.Tr([html.Th(col) for col in filtered_df_3_5.columns])
        ),
        html.Tbody([
            html.Tr([
                html.Td(str(filtered_df_3_5.iloc[i][col])) for col in filtered_df_3_5.columns
            ]) for i in range(len(filtered_df_3_5))
        ])
    ])

    # Correlation matrix for heatmap (including all columns except Total_Load)
    correlation_matrix = df.corr()
    heatmap_fig = go.Figure(data=go.Heatmap(
        z=correlation_matrix.T.values,  # Transpose the matrix here
        x=correlation_matrix.columns.tolist(),  # Use index for x-axis after transpose
        y=correlation_matrix.index.tolist(),  # Use columns for y-axis after transpose
        colorscale='Viridis',
        zmin=-1, zmax=1
    ))
    heatmap_fig.update_layout(title="Correlation Heatmap")

    return fig, table, heatmap_fig, no_data_message, current_height_text

# Run the app in a local browser window
if __name__ == '__main__':
    port = random.randint(8000, 9000)
    app.run_server(debug=True)
