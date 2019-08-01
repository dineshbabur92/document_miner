import base64
import datetime
import io
import dash
from dash.dependencies import Input, Output, State
import dash_core_components as dcc
import dash_html_components as html
import dash_table
import pandas as pd
import tabula
from tabula import wrapper
from six.moves.urllib.parse import quote

external_stylesheets = [
    "https://maxcdn.bootstrapcdn.com/bootstrap/4.0.0/css/bootstrap.min.css",
    "https://fonts.googleapis.com/css?family=Montserrat|Pacifico",
    "https://codepen.io/dineshbabur92/pen/aMQdzV.css"
]

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
app.config['suppress_callback_exceptions']=True

#UI Part 
app.layout = html.Div([

    html.Div(id='navbar', children=[
        html.Div(id="navbar-title", children=["Document Miner"])
    ]),
    #File upload feature
    dcc.Upload(
        id='upload-data',
        children=html.Div([
            html.A('Upload PDF')
        ]),
        # Allow multiple files to be uploaded
        multiple=False,
        className="btn btn-primary"
    ),
    html.Div([
        "Exclude transaction having, ",
        html.Div(dcc.Input(id='exclude-filter-input', type='text'))
        # , html.Button('Submit', id='exclude-filter-button')
    ]),
    #Displays Parsed table from Pdf
    html.Div(id='output-data-upload'),
    #Enable to download the daily balance from a calculated function
    html.Div(id="download-data")
])
@app.server.route('/static/<path:path>')
def static_file(path):
    static_folder = os.path.join("D:\\Pilots\\OCR\\", 'css')
    return send_from_directory(static_folder, path)

import tabula 
import pandas as pd

import warnings
warnings.filterwarnings('ignore')


def pdf_parser_crawford(filenames, filt):
    
    filename0 = filenames[0]
    filename1 = filenames[1]
    
    ### Getting the acc num and name 
    tables= tabula.read_pdf(filename1, multiple_tables=True,output='dataframe',
                                 pages='all',guess = False, pandas_options={'header':False})
    df=tables[0]
    acc_name = df.iat[0,0]
    acc_number = df.iat[2,1]
    df['acc_name'] = acc_name
    df['acc_number'] = acc_number

    tables = tabula.read_pdf(filename0, multiple_tables=True,output='dataframe',
                                     pages='all',guess = True, pandas_options={'header':True})   
    df = tables[0] # getting first table
    transactions = df[2:] # getting only transactions

    def parse_money_to_float(x):
        return float(str(x).replace(",", ""))

    # getting opening and closing balance from first row of parsing
    global clos_bal, open_bal
    open_bal = parse_money_to_float(df["Balance"][1])
    open_bal = float(open_bal)
    clos_bal = open_bal

    # splitting first col merged with date and desc of transaction
    transactions['trans_date'] = transactions['Date Details'].apply(lambda x: " ".join(x.split()[0:2]))
    transactions['trans_desc']= transactions['Date Details'].apply(lambda x: " ".join(x.split()[2:]))

    # converting debit and credits to float and init-ing opening and closing balance
    transactions["debit"] = transactions["Withdrawals"].fillna(0).apply(lambda x: parse_money_to_float(x))
    transactions["credit"] = transactions["Deposits"].fillna(0).apply(lambda x: parse_money_to_float(x))
    transactions["opening_balance"]= 0.0
    transactions["closing_balance"] = 0.0
    transactions["is_filtered"] = True
    transactions["acc_number"] = acc_number
    transactions["acc_name"] = acc_name

    def process_balance_by_row(row, filt):

        global open_bal, clos_bal
    #     print(row.name)
        if filt is None or filt == "" or filt.lower() not in row["trans_desc"].lower():
            clos_bal = open_bal - row["debit"]
            clos_bal = clos_bal + row["credit"]
            row["closing_balance"] = round(clos_bal, 2)
            row["opening_balance"] = round(open_bal, 2)
            row["is_filtered"] = False
            open_bal = clos_bal
        return row
    #     print(row, open_bal, clos_bal)
    #     return row

#     filt = "payroll"
    transactions = transactions.apply(lambda row: process_balance_by_row(row, filt), axis=1)
    target_columns = ["acc_number", "acc_name",
        "trans_date", "trans_desc", "debit", "credit", "opening_balance", "closing_balance"]
    transactions_filtered = transactions[transactions["is_filtered"] == False][target_columns]
    transactions = transactions[target_columns]

    return transactions, transactions_filtered

# global transactions_displayed
# transactions_displayed = None
def generate_table(dataframe, max_rows=10):
    # global transactions_displayed 
    # transactions_displayed = dataframe
    final = dataframe
    csv_string = final.to_csv(index=False, encoding='utf-8')
    csv_string = "data:text/csv;charset=utf-8,%EF%BB%BF" + quote(csv_string)

    return [html.Div([
    dash_table.DataTable(
        data=dataframe.to_dict('rows'),
        columns=[{'name': i, 'id': i} for i in dataframe.columns]
    )]),
    html.A(
        'Download Data',
        id='download-link',
        download="output.csv",
        href=csv_string,
        target="_blank",
        className="btn btn-success"
    )]


@app.callback(
    Output('output-data-upload', 'children'),
    [
        Input("exclude-filter-input", "n_submit"),
        Input('upload-data', 'contents')
    ],
    [
        State('upload-data', 'filename'),
        State('upload-data', 'last_modified'),
        State("exclude-filter-input", "value")
    ]
)
def update_output(n_clicks, list_of_contents, list_of_names, list_of_dates, filter_value):
    print(n_clicks, list_of_names, list_of_dates, filter_value)
    
    if list_of_contents is None:
        return
    
    contents = list_of_contents
    filename = list_of_names
    date = list_of_dates
    
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    
    df, df_filtered  = pdf_parser_crawford([io.BytesIO(decoded),io.BytesIO(decoded)], filter_value)
    return generate_table(df_filtered)
    
# #function for downloading the daily balance    
# @app.callback(Output('download-data', 'children'),
#               [Input('output-data-upload', 'children')])
# def download_csv(balance):
#     if balance is None:
#         return
#     try:
#         data = balance['props']['children'][0]['props']['data']
#         final = pd.dataframe[data]
#         csv_string = final.to_csv(index=False, encoding='utf-8')
#         csv_string = "data:text/csv;charset=utf-8,%EF%BB%BF" + quote(csv_string)
#         return html.A(
#             'Download Data',
#             id='download-link',
#             download="output.csv",
#             href=csv_string,
#             target="_blank",
#             className="btn btn-success"
#         )
#         # transactions_displayed = None
#     except Exception as e:
#         return ""

if __name__ == '__main__':
    app.run_server(debug=True, host="0.0.0.0", port=9099)
