#17 June - contd. from BTST_Sell_12_June.py
#remove default variables from the past
#save dashboard


# 12 June - Today is about auto-sell. 
#Buying from yesterday is working but savinf of default orders has errors

#9 June continued from 8 June file. tat needs to be checked first
# this makes the quantity field editable, these will be big changes

#8 June - fixing default variable tracking, which remains in memory even after app closure

#7 June changed logic for default orders, default orders now placed are multiple of tick size
#but issue persists due to non-tracking of timestamp in default

#28 May - fixing float issues, api call in open orders 
#and default orders placing only one order and throwing exception
#summary page is also done

#23 May - Edit and delete need order_id, incorporating that throughout

#21 May - today we place actual orders (which was written previously) and 
#write code for open orders and executed orders using websocket. 
#Will also try to correct real-time dashboard updates
#delete orders from API
#edit implemented with APIs


import tkinter as tk
import json, os
from tkinter import ttk, messagebox, simpledialog
from tkinter.font import Font
from tkinter import BooleanVar
from datetime import datetime, time, timedelta
from kiteconnect import KiteConnect, KiteTicker
import pandas as pd
import threading
from collections import defaultdict


# API Setup
api_key = ""
access_token = ""
kite = KiteConnect(api_key=api_key)
kite.set_access_token(access_token)

global open_orders, open_default_orders, default_quantities
global selected_row_index
open_orders = []
open_default_orders = []
selected_row_index = None
global order_tree
order_tree = None
global portfolio_name_var
portfolio_name_var = None



# DataFrame columns
columns = ["Check", "Exchange", "Symbol", "Buy Qty", "Buy Price", "Sell Price",
           "% Change", "Last Traded Price", "Sell Qty", "Close", "Open", "High", "Low"]

display_columns = ["Check", "Exchange", "Symbol", "Buy Qty", "Buy Price", "Sell Price", "% Change", "Last Traded Price", "Sell Qty", "Close", "Open", "High", "Low"]

all_columns = ["Check", "Exchange", "Symbol", "Buy Qty", "Buy Price", "Sell Price",
           "% Change", "Last Traded Price", "Sell Qty", "Close", "Open", "High", "Low", "upper_circuit", "lower_circuit"]


# Initializing the DataFrame with a 'Check' column for checkboxes
global df
df = pd.DataFrame(columns=all_columns)
df['Check'] = df['Check'].apply(lambda x: BooleanVar(value=False))
original_df = df.copy()  # making a copy of df to check if portfolio has been changed at the time of closing

global kws
kws = KiteTicker(api_key, access_token)

def fetch_instruments():
    try:
        instruments = kite.instruments()
        #print("instruments",instruments)
        token_symbol_map = {instrument['tradingsymbol'].strip(): instrument['instrument_token'] for instrument in instruments}
        return token_symbol_map
    except Exception as e:
        messagebox.showerror("Error", f"Failed to fetch instruments: {str(e)}")
        return {}


global token_symbol_map
token_symbol_map = fetch_instruments()
#print("token_symbol_map as per api", token_symbol_map)
#token_symbol_map = {
 #   738561: 'TATASTEEL',  # Example token to symbol mapping
  #  21508: 'COCHINSHIP',
   # 17010: 'GENSOL',
    #1672: 'HGINFRA',
#    10905: 'GENESYS',
 #   11060: 'KSOLVES',
  #  14745: 'ADVANIHOTR',
   # 6364: 'NATIONALUM'
#}

def configure_style():
    style = ttk.Style()
    style.theme_use("clam")
    style.configure("Treeview", background="white", foreground="black", fieldbackground="white", rowheight=30, font=('Helvetica', 12))  # Adjust font size for body
    style.configure("Treeview.Heading", font=('Helvetica', 11), background="#f0f0f0", foreground="black")  # Adjust font size and background for header
    style.configure('Treeview.Frame', background='#a0b9d9')  # Match the background color
    style.map('Treeview', background=[('selected', '#0078d7')], foreground=[('selected', 'white')])  # Change selected row color

    # Configure buttons to have a better style
    style.configure('TButton', font=('Helvetica', 10), background='#e0f0ff', foreground='black', padding=(5, 5), relief='flat')
    style.map('TButton', background=[('active', '#0078d7'), ('pressed', '#005a9e')], foreground=[('active', 'white'), ('pressed', 'white')])
    style.configure('TButton', borderwidth=1, focuscolor=style.configure(".")["background"])  # Remove border and focus highlight

def fetch_stock_data(exchange, symbol):
    try:
        data = kite.quote(f"{exchange}:{symbol}")
        #print("kite.quote data", data)
        quote = data[f"{exchange}:{symbol}"]
        print("quote", quote)
        #print("quote",quote)
        ohlc = quote['ohlc']
        return {
            "Exchange": exchange,
            "Symbol": symbol,
            "Buy Qty": quote['buy_quantity'],
            "Buy Price": round(quote['last_price'] - 5, 2),
            "Sell Price": round(quote['last_price'] + 5, 2),
            "% Change": round(((quote['last_price'] - ohlc['close']) / ohlc['close']) * 100, 2),
            "Last Traded Price": round(quote['last_price'], 2),
            "Sell Qty": quote['sell_quantity'],
            "Close": round(ohlc['close'], 2),
            "Open": round(ohlc['open'], 2),
            "High": round(ohlc['high'], 2),
            "Low": round(ohlc['low'], 2),
            "upper_circuit": quote['upper_circuit_limit'],  # Include upper circuit
            "lower_circuit": quote['lower_circuit_limit']   # Include lower circuit
        }
    except Exception as e:
        messagebox.showerror("Data Fetching Error", f"Failed to fetch data for {symbol}: {str(e)}")
        return None
    
def fetch_last_traded_price(exchange, symbol):
    try:
        quote_data = kite.quote(f"{exchange}:{symbol}")
        last_traded_price = quote_data[f"{exchange}:{symbol}"]["last_price"]
        return last_traded_price
    except Exception as e:
        print(f"Error fetching last traded price: {str(e)}")
        return None

def fetch_days_high(exchange, symbol):
    try:
        quote_data = kite.quote(f"{exchange}:{symbol}")
        days_high = quote_data[f"{exchange}:{symbol}"]["ohlc"]["high"]
        return days_high
    except Exception as e:
        print(f"Error fetching day's high: {str(e)}")
        return None

def fetch_positions_and_holdings():
    try:
        positions = kite.positions()
        print("positions", positions)
        holdings = kite.holdings()
        print("holdings", holdings)
        today = datetime.now().date()
        start_of_latest_trading_day = get_start_of_trading_day()
        print("start_of_latest_trading_day", start_of_latest_trading_day)
        
        # Ensure that the positions have the 'timestamp' key
        filtered_positions = [
            position for position in positions['net']
            if 'timestamp' in position and datetime.strptime(position['timestamp'], '%Y-%m-%d %H:%M:%S') >= start_of_latest_trading_day
        ]
        # Ensure that the holdings have the 'last_updated' key
        filtered_holdings = [
            holding for holding in holdings 
            if 'authorised_date' in holding and datetime.strptime(holding['authorised_date'], '%Y-%m-%d %H:%M:%S') >= start_of_latest_trading_day
        ]

        return filtered_positions, filtered_holdings
    except Exception as e:
        messagebox.showerror("Error", f"Failed to fetch positions and holdings: {str(e)}")
        return None, None

def process_positions_and_holdings(positions, holdings):
    summary = []

    for position in positions:
        summary.append({
            "Exchange": position['exchange'],
            "Symbol": position['tradingsymbol'],
            "Buy Qty": position['buy_quantity'],
            "Buy Avg": position['buy_price'],
            "Buy Val": position['buy_value'],
            "Sell Qty": position['sell_quantity'],
            "Sell Avg": position['sell_price'],
            "Sell Val": position['sell_value'],
            "Net Qty": position['quantity'],
            "Net Price": position['last_price'],
            "Net Val": position['pnl']
        })

    for holding in holdings:
        summary.append({
            "Exchange": holding['exchange'],
            "Symbol": holding['tradingsymbol'],
            "Buy Qty": holding['quantity'],
            "Buy Avg": holding['average_price'],
            "Buy Val": holding['last_price'] * holding['quantity'],
            "Sell Qty": 0,
            "Sell Avg": 0,
            "Sell Val": 0,
            "Net Qty": holding['quantity'],
            "Net Price": holding['last_price'],
            "Net Val": holding['pnl']
        })

    return summary

def display_summary_window(summary):
    summary_window = tk.Toplevel()
    summary_window.title("Executed Orders Summary")
    screen_width = summary_window.winfo_screenwidth()
    screen_height = summary_window.winfo_screenheight()
    summary_window.geometry(f"{screen_width}x{screen_height}")
    summary_window.configure(background='#a0b9d9')

    columns = ["Symbol", "Buy Qty", "Buy Avg", "Buy Val", "Sell Qty", "Sell Avg", "Sell Val", "Net Qty", "Net Price", "Net Val"]
    tree = ttk.Treeview(summary_window, columns=columns, show="headings", selectmode="extended")
    tree.pack(side='left', fill='both', expand=True)
    setup_scrollbars(tree, summary_window)

    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, width=Font(family='Helvetica', size=10).measure(col.title()), anchor=tk.CENTER)
    
    total_buy_qty = 0
    total_buy_val = 0
    total_sell_qty = 0
    total_sell_val = 0
    total_net_qty = 0
    total_net_val = 0

    for symbol, data in summary.items():
        values = [symbol]
        for col in columns[1:]:
            values.append(data[col])
        tree.insert('', 'end', values=values)

        total_buy_qty += data["Buy Qty"]
        total_buy_val += data["Buy Val"]
        total_sell_qty += data["Sell Qty"]
        total_sell_val += data["Sell Val"]
        total_net_qty += data["Net Qty"]
        total_net_val += data["Net Val"]

    summary_values = ["Total", total_buy_qty, "", total_buy_val, total_sell_qty, "", total_sell_val, total_net_qty, "", total_net_val]
    tree.insert('', 'end', values=summary_values, tags=('summary',))
    tree.tag_configure('summary', background='#d3d3d3')

    set_focus_on_first_row(tree)
    summary_window.bind('<Escape>', lambda e: summary_window.destroy())
    summary_window.focus_force()

def show_summary(event=None):
    executed_orders = fetch_executed_orders()
    if executed_orders is not None:
        summary = process_executed_orders(executed_orders)
        display_summary_window(summary)

def setup_gui(root):
    global portfolio_name_var
    global selected_row
    selected_row = None

    global selected_row_index
    selected_row_index = None

    global order_tree

    global last_f3_press_time
    last_f3_press_time = datetime.now()
    global last_f8_press_time
    last_f8_press_time = datetime.now()
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()

    root.title("Stock Dashboard - Simulation")
    root.geometry(f"{screen_width}x{screen_height}")
    root.configure(background='#a0b9d9')

    root.bind('<F3>', handle_f3_press)
    root.bind('<F8>', handle_f8_press)
    root.bind('<Shift-F2>', handle_shift_f2_press)
    root.bind('<Alt-F6>', show_summary)
    root.bind('+', lambda event: create_order_window('BUY'))
    root.bind('-', lambda event: create_order_window('SELL'))

    entry_frame = tk.Frame(root, bg='#a0b9d9', padx=10, pady=10)  # Add padding and background color
    entry_frame.pack(side='top', fill='x', expand=False)
    #entry_frame.configure(background='#a0b9d9')  # Match the dropdown frame background

    portfolio_name_label = ttk.Label(entry_frame, textvariable=portfolio_name_var, background='#a0b9d9')
    portfolio_name_label.pack(side='left', padx=15, pady=5)

    ttk.Label(entry_frame, text="Add Scrip from Here:", background='#a0b9d9').pack(side='left')
    exchange_var = tk.StringVar(value="NSE")
    exchange_entry = ttk.Combobox(entry_frame, textvariable=exchange_var, values=["NSE", "BSE"])
    exchange_entry.pack(side='left', padx=5, pady=5)

    ttk.Label(entry_frame, text="Symbol:", background='#a0b9d9').pack(side='left')
    symbol_var = tk.StringVar()
    symbol_entry = ttk.Entry(entry_frame, textvariable=symbol_var)
    symbol_entry.pack(side='left', padx=5, pady=5)
    symbol_entry.bind('<Return>', lambda event: add_stock(exchange_var.get(), symbol_var.get(), tree, root))

    add_button = ttk.Button(entry_frame, text="Add Stock", command=lambda: add_stock(exchange_var.get(), symbol_var.get(), tree, root))
    add_button.pack(side='left', padx=5, pady=5)

    place_orders_button = ttk.Button(entry_frame, text="Place Default Orders", command=lambda: prepare_and_display_orders(tree, root))
    place_orders_button.pack(side='left', padx=15, pady=5)

    summary_button = ttk.Button(entry_frame, text="Show Summary", command=show_summary)
    summary_button.pack(side='left', padx=15, pady=5)

    stream_btn = ttk.Button(entry_frame, text="Start Streaming", command=lambda: start_streaming(tree))
    stream_btn.pack(side='left', padx=15, pady=5)

    sell_orders_button = ttk.Button(entry_frame, text="Place Default Sell Orders", command=lambda: prepare_and_display_sell_orders(tree, root))
    sell_orders_button.pack(side='left', padx=15, pady=5)

    #open_order_button = ttk.Button(entry_frame, text="Open Order for Stock", command=lambda: view_open_orders_for_stock(selected_row))
    #open_order_button.pack(side='left', padx=5, pady=5)

    #all_orders_button = ttk.Button(entry_frame, text="All Open Orders", command=view_all_open_orders)
    #all_orders_button.pack(side='left', padx=5, pady=5)

    #tree_frame = ttk.Frame(root, padding=(10, 10, 10, 10))  # Added padding
    tree_frame = tk.Frame(root, bg='#a0b9d9', padx=10, pady=10)  # Set background color
    tree_frame.pack(side='top', fill='both', expand=True)

    tree = ttk.Treeview(tree_frame, columns=display_columns, show="headings", selectmode="extended")
    tree.pack(side='left', fill='both', expand=True)
    setup_scrollbars(tree, tree_frame)

    tree.bind('<<TreeviewSelect>>', lambda event: on_selection_change(event))
    tree.bind('<Delete>', lambda event: delete_dashboard_row(tree))
    bind_arrow_keys(root, tree)

    for col in display_columns[1:]:
        tree.heading(col, text=col)
        tree.column(col, width=Font(family='Helvetica', size=10).measure(col.title()), anchor=tk.CENTER)
    
    tree.column("#1", width=15)# Adjust width for check column
    tree.column("#3", width=50)  # Adjust width for Symbol column
    tree.bind('<Button-1>', lambda event: toggle_check(event, tree))

    #for col in display_columns:
    #    tree.heading(col, text=col)
    #    tree.column(col, width=Font(family='Helvetica', size=10).measure(col.title()), anchor=tk.CENTER)

    def toggle_check(event, tree):
        row_id = tree.identify_row(event.y)
        column = tree.identify_column(event.x)
            
        if column == '#1':
            current_value = tree.item(row_id, 'values')[0]
            new_value = "✓" if current_value == "✗" else "✗"
            values = list(tree.item(row_id, 'values'))
            values[0] = new_value
            tree.item(row_id, values=values)
    
    return tree

def add_stock(exchange, symbol, tree, root, stock_data=None):
    global df
    symbol = symbol.strip()  # Ensure symbol is stripped of whitespace
    existing_entries = [tree.item(item, 'values') for item in tree.get_children()]
    for entry in existing_entries:
        if entry[2] == symbol and entry[1] == exchange:
            messagebox.showerror("Error", "This symbol and exchange combination already exists.", parent=root)
            return

    if stock_data:
        values = ["✗"] + [stock_data.get(col, "") for col in all_columns if col != "Check"]
        tree.insert('', 'end', values=values)
        new_row = pd.DataFrame([stock_data])
    else:
        data = fetch_stock_data(exchange, symbol)
        if data:
            values = ["✗"] + [data[col] for col in all_columns if col != "Check"]
            tree.insert('', 'end', values=values)
            new_row = pd.DataFrame([data])
        else:
            messagebox.showerror("Error", "Failed to fetch data for the symbol.", parent=root)
            return

    new_row = new_row.dropna(axis=1, how='all')
    df = pd.concat([df, new_row], ignore_index=True)
    print("Updated DataFrame:\n", df)


def on_selection_change(event):
    global selected_row
    global selected_row_index
    selection = event.widget.selection()
    if selection:
        selected_row_index = event.widget.index(selection[0])
        selected_items = event.widget.selection()
        print("Selected Row Index:", selected_row_index)
        print("selected_items", selected_items)
    if selected_items:
        selected_row = event.widget.item(selected_items[0], 'values')
        print("Selected Row:", selected_row)

def setup_scrollbars(tree, frame):
    vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    vsb.pack(side='right', fill='y')
    tree.configure(yscrollcommand=vsb.set)
    #hsb = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
    #hsb.pack(side='bottom', fill='x')
    #tree.configure(xscrollcommand=hsb.set)  

def prepare_and_display_orders(tree, root):
    global open_orders, token_symbol_map
    orders_data = []
    checked_items = [tree.item(item) for item in tree.get_children() if tree.item(item, 'values')[0] == "✓"]
    if not checked_items:
        messagebox.showinfo("Selection Needed", "Please check and select at least one scrip to create the default orders.", parent=root)
        return

    if not open_orders:
        print("No existing orders")
    else:
        response = messagebox.askquestion("Choose Action", "Choose Yes to delete all open orders else Choose No to keep already open orders and create more new ones.", parent=root)
        if response == 'yes':
            print("User chose to clear all existing orders.")
            open_orders = []
        else:
            print("User chose to retain existing orders and create more.")

    for item in checked_items:
        values = item['values']
        symbol = values[2]
        exchange = values[1]
        last_traded_price = float(values[7])
        day_low = float(values[12])
        # Calculate buy prices based on the current price and day's low
        if last_traded_price > day_low * 1.02:
            buy_prices = [last_traded_price * (1 - i / 100) for i in range(2, 8, 2)]
        else:
            buy_prices = [last_traded_price * (1 - i / 100) for i in range(3, 9, 2)]
        tick_size = get_tick_size(symbol)
        buy_prices = [round(price - (price % tick_size), 2) for price in buy_prices]
        # Check if buy prices are below the lower circuit
        #lower_circuit = token_symbol_map[symbol]['lower_circuit_limit']
        #lower_circuit = data[lower_circuit]
        #lower_circuit = day_low*0.95
        lower_circuit = df.loc[(df['Exchange'] == exchange) & (df['Symbol'] == symbol), 'lower_circuit'].values[0]
        print("lower_circuit for ", symbol, "is", lower_circuit)

        buy_prices = [max(price, lower_circuit * 1.001) for price in buy_prices]

        # Create buy orders
        timestamps_buy = ["15:20:00", "15:25:30", "15:28:00"]
        #timestamps_sell = ["09:15:00", "09:17:00", "09:18:00"]

        orders = [{'tradingsymbol': symbol, 'exchange': exchange, 'transaction_type': 'BUY', 'order_type': 'LIMIT', 'quantity': 1, 'product': 'CNC', 'price': price, 'validity': 'DAY', 'variety': 'regular', 'timestamp': ts} for price, ts in zip(buy_prices, timestamps_buy)]
        #orders += [{'tradingsymbol': symbol, 'exchange': exchange, 'transaction_type': 'SELL', 'order_type': 'LIMIT', 'quantity': 1, 'product': 'CNC', 'price': price, 'validity': 'DAY', 'variety': 'regular', 'timestamp': ts} for price, ts in zip(sell_prices, timestamps_sell)]

        orders_data.extend(orders)
    choose_default_quantities(orders_data, root)

def display_orders_window(orders_data, root):
    global order_tree, default_quantities
    print("orders_data passed into display_orders_window:", orders_data)  # Debugging print statement
    order_window = tk.Toplevel(root)
    order_window.title("Place Default Orders")
    screen_width = order_window.winfo_screenwidth()
    screen_height = order_window.winfo_screenheight()
    order_window.geometry(f"{screen_width}x{screen_height}")
    order_window.configure(background='#a0b9d9')

    order_frame = tk.Frame(order_window, bg='#a0b9d9', padx=10, pady=10)
    order_frame.pack(fill='both', expand=True)

    order_tree = ttk.Treeview(order_frame, columns=["tradingsymbol", "exchange", "transaction_type", "order_type", "quantity", "product", "price", "validity", "variety", "timestamp"], show="headings")
    order_tree.pack(expand=True, fill='both')
    order_tree.tag_configure('blue', background='lightblue')
    order_tree.tag_configure('red', background='salmon')

    for col in order_tree['columns']:
        order_tree.heading(col, text=col.capitalize())
        order_tree.column(col, anchor="center", width=Font(family='Helvetica', size=10).measure(col.title()))

    if orders_data:
        for order in orders_data:
            symbol = order['tradingsymbol']
            exchange = order['exchange']
            key = f"{symbol}_{exchange}"
            total_quantity = default_quantities.get(key, 3)  # Get the total quantity for the symbol-exchange combination
            quantity_per_order = total_quantity // 3  # Calculate the quantity for each buy order
            remaining_quantity = total_quantity % 3  # Calculate the remaining quantity
            if remaining_quantity > 0:
                order['quantity'] = quantity_per_order + 1
                remaining_quantity -= 1
            else:
                order['quantity'] = quantity_per_order
            color = 'blue' if order['transaction_type'] == 'BUY' else 'red'
            values = list(order.values())
            order_tree.insert('', 'end', values=values, tags=('blue' if order['transaction_type'] == 'BUY' else 'red',))

    else:
        order_tree.insert('', 'end', values=["No records as per Specifications!"], tags=('no_data',))
        order_tree.tag_configure('no_data', foreground='red')

    setup_scrollbars(order_tree, order_frame)
    set_focus_on_first_row(order_tree)

    def delete_order_from_place_default(order_tree, orders_data):
        selected = order_tree.selection()
        if selected:
            result = messagebox.askquestion("Delete Order", "Are you sure you want to delete this order?", parent=order_frame)
            if result == 'yes':
                selected_order_values = order_tree.item(selected[0], 'values')
                orders_data[:] = [order for order in orders_data if list(order.values()) != list(selected_order_values)]
                order_tree.delete(selected[0])

    order_tree.bind('<Delete>', lambda e: delete_order_from_place_default(order_tree, orders_data))

    place_orders_btn = ttk.Button(order_window, text="Confirm Default Orders", command=lambda: confirm_default_order_details(order_tree, order_window))
    place_orders_btn.pack(side='bottom', padx=10, pady=10)
    order_window.bind('<Escape>', lambda e: order_window.destroy())
    order_window.focus_force()
    order_window.mainloop()
    bind_arrow_keys(order_window, order_tree)

def prepare_and_display_sell_orders(tree, root):
    global open_orders, default_quantities, token_symbol_map
    orders_data = []
    gift_nifty_price = fetch_gift_nifty_price()  # Fetch GIFT Nifty price from API
    print("gift_nifty_price",gift_nifty_price)
    for key, total_quantity in default_quantities.items():
        symbol, exchange = key.split('_')
        data = fetch_stock_data(exchange, symbol)
        print("data from fetch_stock_data", data)
        if data:
            last_traded_price = data['Last Traded Price']
            day_close = data['Close']
            day_high = data['High']
            if gift_nifty_price is not None:  # Check if gift_nifty_price is not None
                if gift_nifty_price > 0:
                    sell_prices = [day_close * (1 + i / 100) for i in [2, 4, 5]]
                    print("sell_prices gift nifty > 0", sell_prices)
                else:
                    sell_prices = [day_close * (1 + i / 100) for i in [0.75, 1.5, 5]]
                    print("sell_prices gift nifty > 0", sell_prices)
            else:
                # Handle the case when gift_nifty_price is None
                print("GIFT Nifty price is not available. Using default sell prices.")
                sell_prices = [day_close * (1 + i / 100) for i in [2, 4, 5]]  # Default sell prices
                        # Check if buy prices are below the lower circuit
            upper_circuit = data['upper_circuit']
            #upper_circuit = token_symbol_map[symbol]['upper_circuit_limit']  

            sell_prices = [min(price, upper_circuit * 0.999) for price in sell_prices]
            print("sell_prices after max with upper circuit", sell_prices)
            tick_size = get_tick_size(symbol)
            sell_prices = [round(price - (price % tick_size), 2) for price in sell_prices]
            print("sell_prices after rounding", sell_prices)
            timestamps_sell = ["9:26:00", "9:24:00", "9:25:00"]
            quantity_per_order = total_quantity // 3
            remaining_quantity = total_quantity % 3
            now = datetime.now()
            is_after_market = (now.time() >= time(15, 45) or now.time() < time(8, 57)) if exchange == 'NSE' else (now.time() >= time(15, 45) or now.time() < time(8, 59))
            for price, ts in zip(sell_prices, timestamps_sell):
                quantity = quantity_per_order
                if remaining_quantity > 0:
                    quantity += 1
                    remaining_quantity -= 1
                orders_data.append({
                    'tradingsymbol': symbol,
                    'exchange': exchange,
                    'transaction_type': 'SELL',
                    'order_type': 'LIMIT',
                    'quantity': quantity,
                    'product': 'CNC',
                    'price': price,
                    'validity': 'DAY',
                    'variety' : 'regular' if not is_after_market else 'amo',
                    'timestamp': ts
                })

    display_orders_window(orders_data, root)


def choose_default_quantities(orders_data, root):
    global default_quantities

    default_window = tk.Toplevel(root)
    default_window.title("Choose Default Quantities")
    default_window.geometry("400x300")
    default_window.configure(background='#a0b9d9')

    default_frame = tk.Frame(default_window, bg='#a0b9d9', padx=10, pady=10)
    default_frame.pack(fill='both', expand=True)

    default_entries = {}

    for order in orders_data:
        symbol = order['tradingsymbol']
        exchange = order['exchange']
        key = f"{symbol}_{exchange}"

        if key not in default_entries:
            tk.Label(default_frame, text=f"{symbol} ({exchange}):", bg='#a0b9d9').pack()
            default_entry = tk.Entry(default_frame)
            default_entry.insert(0, str(default_quantities.get(key, 0)))
            default_entry.pack()

            default_entries[key] = default_entry

    def confirm_default_quantities():
        global default_quantities

        for key, entry in default_entries.items():
            default_quantities[key] = int(entry.get())

        default_window.destroy()
        display_orders_window(orders_data, root)

    confirm_button = ttk.Button(default_window, text="Confirm Default Quantities", command=confirm_default_quantities)
    confirm_button.pack(pady=10)

def update_default_quantities(orders_data):
    global default_quantities, order_tree
    default_quantities = {}
    for order in orders_data:
        symbol = order['tradingsymbol']
        exchange = order['exchange']
        key = f"{symbol}_{exchange}"
        if key not in default_quantities:
            default_quantities[key] = 0
        default_quantities[key] += order['quantity']  # Get the quantity from the order data

    for key in default_quantities:
        total_quantity = default_quantities[key]
        num_orders = len([order for order in orders_data if order['tradingsymbol'] == key.split('_')[0] and order['exchange'] == key.split('_')[1]])
        quantity_per_order = total_quantity // num_orders
        print("quantity_per_order",quantity_per_order)
        remaining_quantity = total_quantity % num_orders
        print("remaining_quantity",remaining_quantity)

        for item_id in order_tree.get_children():
            values = order_tree.item(item_id, 'values')
            if values[0] == key.split('_')[0] and values[1] == key.split('_')[1]:
                quantity_entry = order_tree.set(item_id, '#5')
                if remaining_quantity > 0:
                    quantity_entry.delete(0, tk.END)
                    quantity_entry.insert(0, str(quantity_per_order + 1))
                    remaining_quantity -= 1
                else:
                    quantity_entry.delete(0, tk.END)
                    quantity_entry.insert(0, str(quantity_per_order))

    print("Updated default quantities:", default_quantities)  # Debugging print statement

def handle_f3_press(event):
    """Handle the F3 key press event to open order details."""
    global last_f3_press_time, selected_row
    current_time = datetime.now()
    print("DIFFErence in F3 key presses", (current_time - last_f3_press_time).total_seconds())
    if (current_time - last_f3_press_time).total_seconds() < 1:
            view_all_open_orders()
            print("openining double F3")       
    else:
        if selected_row:
            view_open_orders_for_stock(selected_row)
            print("openining single F3")

        else:
            messagebox.showinfo("No Selection", "Please select a row first.")
    last_f3_press_time = current_time
    #print("F3 press handled correctly.")

def handle_shift_f2_press(event):
    """Open the edit window based on the selected order ID."""
    global selected_row
    if selected_row:
        columns = order_tree["columns"]
        order_id_index = columns.index("order_id")
        order_id = selected_row[order_id_index]
        print(f"Editing order with ID: {order_id}")
        open_edit_window(order_id)
    else:
        print("No row selected for editing or index out of range.")

def handle_f8_press(event):
    """Handle the F8 key press event to open executed order details."""
    global last_f8_press_time, selected_row
    current_time = datetime.now()
    print("Difference in F8 key presses", (current_time - last_f8_press_time).total_seconds())
    if (current_time - last_f8_press_time).total_seconds() < 1:
        view_all_executed_orders()
        print("Opening all executed orders")
    else:
        if selected_row:
            view_executed_orders_for_stock(selected_row)
            print("Opening executed orders for selected stock")
        else:
            print("No Selection in single F8")
            #messagebox.showinfo("No Selection", "Please select a row first.")
    last_f8_press_time = current_time
    #print("F8 press handled correctly.")

def fetch_executed_orders():
    try:
        orders = kite.orders()
        #print("Fetched orders:", orders)  # Debugging line
        start_of_latest_trading_day = get_start_of_trading_day()
        #print("start_of_latest_trading_day", start_of_latest_trading_day)  # Debugging line

        executed_orders = [
            order for order in orders 
            if order['status'] == 'COMPLETE' and 
            datetime.strptime(order['order_timestamp'].strftime('%Y-%m-%d %H:%M:%S') if isinstance(order['order_timestamp'], datetime) else order['order_timestamp'], '%Y-%m-%d %H:%M:%S') >= start_of_latest_trading_day
        ]
        #print("Filtered executed orders:", executed_orders)  # Debugging line
        return executed_orders
    except Exception as e:
        messagebox.showerror("Fetch Error", f"Failed to fetch executed orders: {str(e)}")
        return []
    
def process_executed_orders(executed_orders):
    summary = defaultdict(lambda: {
        "Buy Qty": 0, "Buy Avg": 0, "Buy Val": 0, 
        "Sell Qty": 0, "Sell Avg": 0, "Sell Val": 0,
        "Net Qty": 0, "Net Price": 0, "Net Val": 0
    })

    for order in executed_orders:
        symbol = order['tradingsymbol']
        if order['transaction_type'] == 'BUY':
            summary[symbol]["Buy Qty"] += order['quantity']
            summary[symbol]["Buy Val"] += order['average_price'] * order['quantity']
        else:
            summary[symbol]["Sell Qty"] += order['quantity']
            summary[symbol]["Sell Val"] += order['average_price'] * order['quantity']

    for symbol in summary:
        if summary[symbol]["Buy Qty"] > 0:
            summary[symbol]["Buy Avg"] = summary[symbol]["Buy Val"] / summary[symbol]["Buy Qty"]
        if summary[symbol]["Sell Qty"] > 0:
            summary[symbol]["Sell Avg"] = summary[symbol]["Sell Val"] / summary[symbol]["Sell Qty"]
        summary[symbol]["Net Qty"] = summary[symbol]["Buy Qty"] - summary[symbol]["Sell Qty"]
        summary[symbol]["Net Val"] = summary[symbol]["Buy Val"] - summary[symbol]["Sell Val"]
        summary[symbol]["Net Price"] = summary[symbol]["Net Val"] / summary[symbol]["Net Qty"] if summary[symbol]["Net Qty"] != 0 else 0

    return summary

def view_executed_orders_for_stock(selected_row):
    executed_orders = fetch_executed_orders()
    stock_orders = [order for order in executed_orders if order['tradingsymbol'] == selected_row[2]]
    display_executed_orders(stock_orders, f"Executed Orders for {selected_row[2]}")

def view_all_executed_orders():
    executed_orders = fetch_executed_orders()
    display_executed_orders(executed_orders, "All Executed Orders")

def display_executed_orders(orders, title):
    executed_orders_window = tk.Toplevel()
    executed_orders_window.title(title)
    screen_width = executed_orders_window.winfo_screenwidth()
    screen_height = executed_orders_window.winfo_screenheight()
    executed_orders_window.geometry(f"{screen_width}x{screen_height}")
    executed_orders_window.configure(background='#a0b9d9')

    columns = ["TraderId", "Symbol/ScripId", "Series", "Order Type", "B/S", "Quantity", "Price", "Client", "Client ID", "Exchange", "Trade No.", "Time", "Product Type"]
    tree = ttk.Treeview(executed_orders_window, columns=columns, show="headings", selectmode="extended")
    tree.pack(side='left', fill='both', expand=True)
    tree.tag_configure('blue', background='lightblue')
    tree.tag_configure('red', background='salmon')
    setup_scrollbars(tree, executed_orders_window)

    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, width=Font(family='Helvetica', size=10).measure(col.title()), anchor=tk.CENTER)

    print("Orders to display:", orders)  # Debugging line

    # Map the Kite API order keys to the Treeview columns
    column_mapping = {
        "TraderId": "placed_by",
        "Symbol/ScripId": "tradingsymbol",
        "Series": "exchange",
        "Order Type": "order_type",
        "B/S": "transaction_type",
        "Quantity": "quantity",
        "Price": "average_price",
        "Client": "client",  # If "client" is not available in the order data, you may need to handle it.
        "Client ID": "account_id",
        "Exchange": "exchange",
        "Trade No.": "exchange_order_id",
        "Time": "order_timestamp",
        "Product Type": "product"
    }

    if orders:
        for order in orders:
            values = []
            for col in columns:
                key = column_mapping.get(col, "")
                value = order.get(key, "")
                # Format datetime value
                if isinstance(value, datetime):
                    value = value.strftime('%Y-%m-%d %H:%M:%S')
                values.append(value)

            color = 'blue' if order['transaction_type'] == 'BUY' else 'red'
            print("Order values:", values)  # Debugging line
            tree.insert('', 'end', values=values, tags=(color,))

    else:
        tree.insert('', 'end', values=["No records as per Specifications!"] + [""] * (len(columns) - 1))
        tree.tag_configure('info', foreground='red')

    executed_orders_window.bind('<Escape>', lambda e: executed_orders_window.destroy())
    executed_orders_window.bind('<Alt-F6>', show_summary)
    executed_orders_window.bind('<F8>', handle_f8_press)
    executed_orders_window.focus_force()

def get_start_of_trading_day():
    now = datetime.now()
    if now.time() < time(9, 0):
        last_trading_day = now - timedelta(days=1)
        while last_trading_day.weekday() >= 5:  # 5: Saturday, 6: Sunday
            last_trading_day -= timedelta(days=1)
        start_of_trading_day = datetime.combine(last_trading_day, time(9, 0))
    else:
        start_of_trading_day = datetime.combine(now.date(), time(9, 0))
    return start_of_trading_day

def confirm_default_order_details(order_tree, order_window):
    global open_orders, default_quantities
    print(f"order_tree in confirm_default_order_details: {order_tree}")
    if not order_tree.winfo_exists():
        print("Error: order_tree reference is invalid.")
        return
    for item in order_tree.get_children():
        try:
            print("item inside for", item)
            order_details = order_tree.item(item, 'values')
            print("order_details", order_details)
            timestamp = order_details[9]  # Assuming the timestamp is at index 9 in the order_details list
            quantity = int(order_details[4])  # Get the quantity from the order_details
            #order_id = submit_order_to_kite(order_window, order_details[0], order_details[1], order_details[4], order_details[6], order_details[2])
            order_id = submit_order_to_kite(order_window, order_details[0], order_details[1], quantity, order_details[6], order_details[2], timestamp, is_default_order=True)
            order_details = kite.order_history(order_id)[-1]
        except Exception as e:
            print(f"Exception in processing order: {e}")
    save_default_quantities()  # Save the default quantities to a file
    order_window.destroy()

def view_all_open_orders():
    global open_orders
    orders = kite.orders()
    #print("orders received from APIs in open orders for stock", orders)
    open_orders = [order for order in orders if order['status'] in ['OPEN', 'TRIGGER PENDING', 'AMO REQ RECEIVED', 'MODIFY AMO REQ RECEIVED','MODIFY AMO', 'AMO REQ PROCESSING', 'TRIGGER PENDING', 'VALIDATION PENDING']]
    #print("global open_orders in view_all_open_orders", open_orders)
    try:
        display_orders(open_orders)
    except Exception as e:
        messagebox.showerror("Error", f"Failed to fetch open orders: {str(e)}")

def view_open_orders_for_stock(selected_row):
    global open_orders
    orders = kite.orders()
    #print("orders received from APIs in open orders for stock", orders)
    open_orders = [order for order in orders if order['status'] in ['OPEN', 'TRIGGER PENDING', 'AMO REQ RECEIVED', 'MODIFY AMO REQ RECEIVED','MODIFY AMO', 'AMO REQ PROCESSING', 'TRIGGER PENDING', 'VALIDATION PENDING']]
    #print("global open_orders in view_open_orders_for_stock", open_orders)
    #print("global selected_row in view_open_orders_for_stock", selected_row)
    if selected_row:
        stock_orders = [order for order in open_orders if order['tradingsymbol'] == selected_row[2]]
        if stock_orders:
            display_orders(stock_orders)
        else:
            display_orders([])
            print(f"No open orders found for {selected_row[2]}")
    else:
        print("No stock row selected")
        #messagebox.showinfo("No Selection", "No stock selected.", parent = new_window)

def display_orders(orders):
    global order_tree

    new_window = tk.Toplevel()
    new_window.title("Orders book - [Pending]")
    screen_width = new_window.winfo_screenwidth()
    new_window.geometry(f"{screen_width}x600")
    new_window.configure(background='#a0b9d9')  # Set background color
    new_window.bind('<Escape>', lambda e: new_window.destroy())
    new_window.focus_force()
    new_window.bind('<F3>', handle_f3_press)

    #order_frame = tk.Frame(new_window, bg='#a0b9d9', padx=10, pady=10)  # Set background color and padding
    #order_frame.pack(fill='both', expand=True)
    
    order_tree = ttk.Treeview(new_window, columns=["tradingsymbol", "transaction_type", "price", "exchange", "order_type", "quantity", "product", "validity", "variety", "status", "order_id"], show="headings")
    order_tree.pack(expand=True, fill='both')

    # Configure the colors for the tags
    order_tree.tag_configure('blue', background='lightblue')
    order_tree.tag_configure('red', background='salmon')

    for col in order_tree['columns']:
        order_tree.heading(col, text=col.capitalize())
        order_tree.column(col, anchor="center", width=20)
    if orders:
        for order in orders:
            try:
                color = 'blue' if order.get('transaction_type', '') == 'BUY' else 'red'
                values = [order.get(key, '') for key in order_tree["columns"]]
                order_tree.insert('', 'end', values=values, tags=(color,))
            except KeyError as e:
                print(f"KeyError: {str(e)} in order {order}")
            except Exception as e:
                print(f"An error occurred: {str(e)}")
        set_focus_on_first_row(order_tree)
        vsb = ttk.Scrollbar(new_window, orient="vertical", command=order_tree.yview)
        vsb.pack(side='right', fill='y')
        order_tree.configure(yscrollcommand=vsb.set)
        hsb = ttk.Scrollbar(new_window, orient="horizontal", command=order_tree.xview)
        hsb.pack(side='bottom', fill='x')
        order_tree.configure(xscrollcommand=hsb.set)
        order_tree.bind('<<TreeviewSelect>>', lambda event: on_selection_change(event))
    else:
        #messagebox.showinfo("No Orders", "There are no orders to display.", parent = new_window)
        order_tree.insert('', 'end', values=["No records as per Specifications!"], tags=('no_data',))
        order_tree.tag_configure('no_data', foreground='red')

    new_window.bind('<Shift-F2>', handle_shift_f2_press)
    new_window.bind('<Alt-F6>', show_summary)
    order_tree.bind('<Delete>', lambda event: delete_open_order(new_window, event, order_tree))

def open_edit_window(order_id):
    global open_orders
    print("order_id passed into open_edit window function", order_id)

    order_details = next((order for order in open_orders if order['order_id'] == order_id), None)
    
    if not order_details:
        messagebox.showerror("Error", f"Order with ID {order_id} not found.")
        return

    edit_window = tk.Toplevel()
    edit_window.title("Edit Order")
    screen_width = edit_window.winfo_screenwidth()
    edit_window.geometry(f"{screen_width}x100")
    labels = ["tradingsymbol", "transaction_type", "price", "exchange", "order_type", "quantity", "product", "validity", "variety", "order_id", "timestamp"]
    entries = {}
    edit_window.bind('<Escape>', lambda e: edit_window.destroy())
    edit_window.focus_force()

    for i, label in enumerate(labels): 
        tk.Label(edit_window, text=label).grid(row=0, column=i, padx=10, pady=5)
        entry = tk.Entry(edit_window, width=20, readonlybackground='lightgray', fg='black')
        entry.grid(row=1, column=i)
        entry.insert(0, order_details.get(label, ""))  # Use dict.get() with default value ""
        entries[label] = entry
        if label not in ["quantity", "price"]:
            entry.configure(state='readonly')

    def submit_changes():
        global open_orders
        try:
            updated_quantity = int(entries["quantity"].get())
            updated_price = float(entries["price"].get())

            kite.modify_order(
                variety=order_details['variety'],
                order_id=order_id,
                quantity=updated_quantity,
                price=updated_price
            )

            for order in open_orders:
                if order['order_id'] == order_id:
                    order['quantity'] = updated_quantity
                    order['price'] = updated_price
                    break

            refresh_order_tree()
            edit_window.destroy()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to modify order: {str(e)}")

    edit_window.bind('<Return>', lambda event: submit_changes())
    entries["quantity"].focus_set()
    entries["quantity"].bind('<Tab>', lambda event: focus_next_widget(event, entries["price"]))
    entries["price"].bind('<Tab>', lambda event: focus_next_widget(event, submit_button))

    submit_button = tk.Button(edit_window, text="Submit Changes", command=submit_changes)
    submit_button.grid(row=2, column=0, columnspan=len(labels), pady=10)

def update_global_open_orders(updated_order):
    global open_orders
    open_orders.append(updated_order)
    refresh_order_tree()
    print("Open orders updated:", open_orders)

def fetch_gift_nifty_price():  
    try:
        #nifty_50_symbol = "NIFTY_50"
        nifty_50_symbol = "NIFTY"
        quote_data = kite.quote(f"NSE:{nifty_50_symbol}")
        print("kite.quote output for NSE:", nifty_50_symbol, "is", quote_data)
        if quote_data:
            last_traded_price = quote_data[f"NSE:{nifty_50_symbol}"]["last_price"]
            print("last nifty price", last_traded_price)
            ohlc = quote_data[f"NSE:{nifty_50_symbol}"]["ohlc"]
            prev_close = ohlc["close"]
            percentage_change = (last_traded_price - prev_close) / prev_close * 100
            print(f"Symbol: {nifty_50_symbol}, Last Traded Price: {last_traded_price}, Previous Close: {prev_close}, Percentage Change: {percentage_change}")
            return percentage_change
    except Exception as e:
        print(f"Error fetching Nifty 50 percentage change: {str(e)}")
        return None
    

def validate_integer(value):
    return value.isdigit() and int(value) > 0

def fetch_open_orders():
    print("inside fetch_open_orders")
    try:
        orders = kite.orders()
        print("orders", orders)
        open_orders = [order for order in orders if order['status'] in ['OPEN', 'TRIGGER PENDING', 'AMO REQ RECEIVED', 'MODIFY AMO REQ RECEIVED', 'MODIFY AMO', 'AMO REQ PROCESSING', 'TRIGGER PENDING', 'VALIDATION PENDING']]
        update_order_list(open_orders)
    except Exception as e:
        print("throwing exception in fetch_open_orders")
        messagebox.showerror("Error", str(e))

def update_order_list(orders):
    global open_orders
    open_orders = orders
    display_orders_in_ui(open_orders)

def display_orders_in_ui(orders):
    global order_tree
    print("inside display_orders_in_ui")

    if not order_tree:
        return
    else:
        order_tree.delete(*order_tree.get_children())  # Clear existing entries
    for order in orders:
        values = [
            order['tradingsymbol'],
            order['exchange'],
            order['transaction_type'],
            order['order_type'],
            order['quantity'],
            order['product'],
            order['price'],
            order['validity'],
            order['variety'],
            order['status'],
            order['order_id']
        ]
        order_tree.insert('', 'end', values=values)

def bind_arrow_keys(window, tree):
    def focus_first_row(event):
        if tree.get_children():
            tree.focus(tree.get_children()[0])
            tree.selection_set(tree.get_children()[0])
     #window.bind('<Up>', focus_first_row)
    #window.bind('<Down>', focus_first_row)
    #window.bind('<Left>', focus_first_row)
    #window.bind('<Right>', focus_first_row)

def delete_dashboard_row(tree):
    selected = tree.selection()
    if selected:
        tree.delete(selected[0])

def delete_open_order(window, event, order_tree):
    selected = order_tree.selection()
    if selected:
        result = messagebox.askquestion("Delete", "Do you want to delete the selected order?", icon='warning')
        if result == 'yes':
            order_details = order_tree.item(selected[0], 'values')
            print("order_details inside delete function",order_details)

            order_id = order_details[10]
            variety = order_details[8]
            print("order_id inside delete function",order_id)

            try:
                kite.cancel_order(variety=variety, order_id=order_id)
                messagebox.showinfo("Success", "Order deleted successfully from Kite.", parent = window)
                global open_orders, open_default_orders
                open_orders = [order for order in open_orders if order['order_id'] != order_id]
                open_default_orders = [order for order in open_default_orders if order['order_id'] != order_id]
                print(f"Removed order from default orders: {open_default_orders}")  # Debugging print statement
                refresh_order_tree()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete order: {str(e)}", parent = window)

def on_ticks(ws, ticks, tree):
    print("Ticks received:", ticks)
    global token_symbol_map
    for tick in ticks:
        symbol = next((key for key, value in token_symbol_map.items() if value == tick['instrument_token']), None)
        last_price = tick['last_price']
        buy_quantity = sum([entry['quantity'] for entry in tick['depth']['buy']])
        sell_quantity = sum([entry['quantity'] for entry in tick['depth']['sell']])

        #if symbol and df[df['Symbol'] == symbol].any():
        if symbol:
            # Update DataFrame with new tick data
            df.loc[df['Symbol'] == symbol, 'Last Traded Price'] = tick['last_price']
            df.loc[df['Symbol'] == symbol, 'Buy Qty'] = buy_quantity
            df.loc[df['Symbol'] == symbol, 'Buy Price'] = tick.get('depth', {}).get('buy', [{}])[0].get('price', df.loc[df['Symbol'] == symbol, 'Buy Price'])
            df.loc[df['Symbol'] == symbol, 'Sell Qty'] = sell_quantity
            df.loc[df['Symbol'] == symbol, 'Sell Price'] = tick.get('depth', {}).get('sell', [{}])[0].get('price', df.loc[df['Symbol'] == symbol, 'Sell Price'])
            df.loc[df['Symbol'] == symbol, '% Change'] = round((last_price - df.loc[df['Symbol'] == symbol, 'Close']) / df.loc[df['Symbol'] == symbol, 'Close'] * 100, 2)
            df.loc[df['Symbol'] == symbol, 'Open'] = tick['ohlc']['open']
            df.loc[df['Symbol'] == symbol, 'High'] = tick['ohlc']['high']
            main_window.after(0, update_gui, tree, symbol)

def update_gui(tree, symbol):
    print("inside update_gui ")
    for child in tree.get_children():
        values = tree.item(child, 'values')
        if values[2] == symbol:
            new_values = df[df['Symbol'] == symbol].iloc[0].tolist()[1:]
            new_values.insert(0, values[0])  # Retain the 'Check' value
            new_values[1] = values[1]  # Retain the 'Exchange' value
            new_values[6] = f"{float(new_values[6]):.2f}"  # Ensure % Change is rounded to two decimal places
            tree.item(child, values=new_values)

def on_connect(ws, response):
    print("Connected successfully")

    global token_symbol_map
    print("df['Symbol']", df['Symbol'])

    # Ensure the symbols are in the correct format and strip any whitespace
    symbols = df['Symbol'].str.strip().tolist()
    tokens = [token_symbol_map.get(symbol, None) for symbol in symbols if symbol in token_symbol_map]
    tokens = [token for token in tokens if token is not None]  # Remove any None values
    print("tokens", tokens)

    if tokens:
        ws.subscribe(tokens)
        ws.set_mode(ws.MODE_FULL, tokens)
    else:
        print("No valid tokens found for subscription.")
        messagebox.showerror("WebSocket Error", "No valid tokens found for subscription.")



def on_error(ws, code, reason):
    messagebox.showerror("WebSocket Error", f"Error {code}: {reason}")

def start_streaming(tree):
    print("inside start_streaming")
    global kws
    #kws.on_ticks = on_ticks
    kws.on_ticks = lambda ws, ticks: on_ticks(ws, ticks, tree)
    kws.on_connect = on_connect
    kws.on_error = on_error
    kws.on_order_update = on_order_update
    try:
        thread = threading.Thread(target=kws.connect)
        thread.start()
    except Exception as e:
        messagebox.showerror("WebSocket Connection Error", f"Error: {str(e)}")

def on_order_update(ws, data):
    print("Order Update received:", data)

    for order in open_orders:
        if order['order_id'] == data['order_id']:
            order.update(data)
            break
    else:
        open_orders.append(data)
    refresh_order_tree()

def update_order_in_ui(order_update):
    print("inside update_order_in_ui")

    global open_orders
    for i, order in enumerate(open_orders):
        if order['order_id'] == order_update['order_id']:
            open_orders[i].update(order_update)
            break
    else:
        open_orders.append(order_update)
    display_orders_in_ui(open_orders)

def start_kws():
    print("inside start_kws")
    kws.connect(threaded=True)

def create_order_window(transaction_type):
    print("create_order_window", transaction_type)
    if not selected_row:
        messagebox.showwarning("No Selection", "Please select a stock row first.", parent=place_order_window)
        return

    color = 'blue' if transaction_type == 'BUY' else 'red'
    place_order_window = tk.Toplevel()
    place_order_window.title(f"{transaction_type} Order Entry")
    screen_width = place_order_window.winfo_screenwidth()
    place_order_window.geometry(f"{screen_width}x100")

    place_order_window.config(bg=color)

    try:
        last_sell_price = float(selected_row[6]) if selected_row[6] else 0.00
    except ValueError:
        last_sell_price = 0.00

    try:
        last_buy_price = float(selected_row[4]) if selected_row[4] else 0.00
    except ValueError:
        last_buy_price = 0.00
    
    price_value = last_sell_price if transaction_type == 'BUY' else last_buy_price
    print("price_value",price_value)

    fields = {
        "Exchange": selected_row[1],
        "Symbol": selected_row[2],
        "Quantity": "1",
        "Price": price_value,
        "Product Type": "CNC"
    }

    ttk.Label(place_order_window, text="Exchange:", background=color).grid(row=0, column=0, padx=10, pady=5)
    exchange_label = ttk.Label(place_order_window, text=fields["Exchange"], background=color)
    exchange_label.grid(row=0, column=1)

    ttk.Label(place_order_window, text="Symbol:", background=color).grid(row=0, column=2, padx=10, pady=5)
    symbol_label = ttk.Label(place_order_window, text=fields["Symbol"], background=color)
    symbol_label.grid(row=0, column=3)

    ttk.Label(place_order_window, text="Quantity:", background=color).grid(row=1, column=0, padx=10, pady=5)
    qty_entry = ttk.Entry(place_order_window, validate="key", validatecommand=(place_order_window.register(validate_integer), '%P'))
    qty_entry.grid(row=1, column=1)
    qty_entry.insert(0, fields["Quantity"])

    ttk.Label(place_order_window, text="Price:", background=color).grid(row=1, column=2, padx=10, pady=5)
    price_entry = ttk.Entry(place_order_window, validate="key", validatecommand=(place_order_window.register(validate_float), '%P'))
    price_entry.grid(row=1, column=3)
    try:
        price_entry.insert(0, f"{float(fields['Price']):.2f}")
        print("price_entry", price_entry)
    except ValueError:
        price_entry.insert(0, "0.00")

    def submit_order():
        price = float(price_entry.get())
        tick_size = get_tick_size(fields["Symbol"])
        print("price",price)
        print("price % tick_size", (price % tick_size))
        tolerance = 1e-9  # Small tolerance to account for floating-point precision issues
        if not (abs(price % tick_size) < tolerance or abs(tick_size - (price % tick_size)) < tolerance):
            messagebox.showerror("Error", f"Price must be a multiple of the tick size ({tick_size})", parent=place_order_window)
            price_entry.focus_set()
            return
        submit_order_to_kite(place_order_window, fields["Symbol"], fields["Exchange"], qty_entry.get(), price_entry.get(), transaction_type)
        place_order_window.destroy()

    submit_btn = ttk.Button(place_order_window, text="Submit", command=submit_order)
    submit_btn.grid(row=2, column=1, columnspan=2, pady=10)

    qty_entry.focus_set()
    qty_entry.bind('<Tab>', lambda event: focus_next_widget(event, price_entry))
    price_entry.bind('<Tab>', lambda event: focus_next_widget(event, submit_btn))
    place_order_window.bind('<Return>', lambda event: submit_order())
    place_order_window.bind('<Escape>', lambda e: place_order_window.destroy())
    place_order_window.bind('<Alt-F6>', show_summary)

    place_order_window.focus_force()

def validate_float(value):
    try:
        float(value)
        return True
    except ValueError:
        return False
    
def get_tick_size(symbol):
    global token_symbol_map
    print("inside get_tick_size FOR SYMBOL token_symbol_map[symbol]", token_symbol_map[symbol])
    try:
        tick_size = token_symbol_map[symbol]['tick_size']
        print("returing tick size", tick_size)
        return tick_size
    except Exception as e:
        print("returning default tick size 0.05")
        return 0.05

def submit_order_to_kite(window, symbol, exchange, quantity, price, transaction_type, timestamp=None, is_default_order=False):
    try:
        if transaction_type == "SELL":
            holdings = kite.holdings()
            stock_holding = next((holding for holding in holdings if holding['tradingsymbol'] == symbol and holding['exchange'] == exchange), None)
            
            if not stock_holding or stock_holding['quantity'] < int(quantity):
                print("Insufficient holdings for this sell order.", symbol)
                #messagebox.showerror("Error", "Insufficient holdings for this sell order.", parent=window)
                #return

        now = datetime.now()
        is_after_market = (now.time() >= time(15, 45) or now.time() < time(8, 57)) if exchange == 'NSE' else (now.time() >= time(15, 45) or now.time() < time(8, 59))

        order_params = {
            "tradingsymbol": symbol,
            "exchange": exchange,
            "transaction_type": transaction_type,
            "order_type": "LIMIT",
            "quantity": int(quantity),
            "product": "CNC",
            "validity": "DAY",
            "variety" : "regular"  if not is_after_market else "amo"
        }
        print("printing before tick size call in submit to kite")
        tick_size = get_tick_size(symbol)
        tolerance = 1e-9  # Small tolerance to account for floating-point precision issues
        # Ensure the price is a multiple of the tick size
        #if not (abs(price % tick_size) < tolerance or abs(tick_size - (price % tick_size)) < tolerance):
         #   messagebox.showerror("Error", f"Price must be a multiple of the tick size ({tick_size})", parent=window)
          #  return None
        # Set the price in the order parameters
        print("printing after tick size call in submit to kite")

        #order_params["price"] = float(price)
        order_params["price"] = price
        print("printing after 22222 tick size call in submit to kite")

        valid_keys = ["tradingsymbol", "exchange", "transaction_type", "order_type", "quantity", "price", "product", "validity", "variety", "disclosed_quantity", "trigger_price", "squareoff","stoploss", "trailing_stoploss", "tag"]
        filtered_params = {key: order_params[key] for key in valid_keys if key in order_params}

        order_id = kite.place_order(**filtered_params)
        messagebox.showinfo("Success", f"Order placed successfully! Order ID: {order_id}", parent=window)

        # Fetch order details using the order_id
        order_details = kite.order_history(order_id)[-1]  # Get the latest order status
        print("Order Details fetched:", order_details)

        # Update the global open_orders list with the new order details
        global open_orders, open_default_orders
        open_orders.append(order_details)
        if is_default_order and timestamp:
            order_details['timestamp'] = timestamp
            open_default_orders.append(order_details)
            #print(f"Added order to default orders: {open_default_orders}")  # Debugging print statement

        return order_id

    except Exception as e:
        messagebox.showerror("Error", str(e), parent=window)
        return None

def focus_next_widget(event, widget):
    widget.focus_set()
    return "break"

def select_all_text(event):
    event.widget.select_range(0, tk.END)
    event.widget.icursor(tk.END)

def refresh_order_tree():
    global order_tree
    global open_orders
    if order_tree:
        order_tree.delete(*order_tree.get_children())
        for order in open_orders:
            order_tree.insert('', 'end', values=list(order.values()))

def set_focus_on_first_row(tree):
    print("empty function for now")
    #if tree.get_children():
    #    tree.focus(tree.get_children()[0])
    #    tree.selection_set(tree.get_children()[0])
    #    tree.tag_configure('focus', background='#0078d7', foreground='white')  # Change focus color

def close_window(window):
    window.destroy()

def check_and_modify_orders():
    global open_orders, open_default_orders
    orders = kite.orders()
    open_orders = [order for order in orders if order['status'] in ['OPEN', 'TRIGGER PENDING', 'AMO REQ RECEIVED', 'MODIFY AMO REQ RECEIVED','MODIFY AMO', 'AMO REQ PROCESSING', 'TRIGGER PENDING', 'VALIDATION PENDING']]
    current_time = datetime.now().strftime("%H:%M:%S")
    print("inside check_and_modify_orders", current_time)
    #print("open_orders", open_orders)
    #print("open_default_orders", open_default_orders)
    for order in open_default_orders:
        print("order['timestamp']", order['timestamp'])
        #print("current_time", current_time)
        if order['timestamp'] <= current_time:
            print("inside if order['timestamp'] <= current_time:")
            order_id = order.get('order_id')
            if order_id:
                # Check if the order ID exists in the open orders
                if not any(o['order_id'] == order_id for o in open_orders):
                    print(f"Order {order_id} not found in open orders. Removing from default orders.")  # Debugging print statement
                    open_default_orders.remove(order)
                else:
                    if order['transaction_type'] == 'SELL' and order['variety'] == 'amo':
                        if current_time >= '09:04:00' and current_time < '09:15:00':
                            # Fetch last traded price and day's high for the stock
                            symbol = order['tradingsymbol']
                            exchange = order['exchange']
                            last_traded_price = fetch_last_traded_price(exchange, symbol)
                            days_high = fetch_days_high(exchange, symbol)
                            
                            # Modify the 9:15 timestamp AMO sell order price
                            if order['timestamp'] == '09:15:00':
                                new_price = min(last_traded_price * 0.9995, days_high * 0.9995)
                                try:
                                    # Modify the order price
                                    modified_order = kite.modify_order(
                                        #variety=order['variety'],
                                        variety='regular',
                                        order_id=order_id,
                                        price=new_price
                                    )
                                    print(f"Modified AMO sell order {order_id} price to {new_price}.")  # Debugging print statement
                                except Exception as e:
                                    print(f"Error modifying AMO sell order {order_id} price: {str(e)}")
                        elif current_time >= '09:15:00':
                            # Modify the open default sell orders to execute at the specified timestamps
                            try:
                                # Modify the order from AMO to MARKET
                                modified_order = kite.modify_order(
                                    #variety=order['variety'],
                                    variety='regular',
                                    order_id=order_id, #error in this line if you don't have system open befoe 9.07 or 9.15
                                    order_type='MARKET'
                                )
                                print(f"Modified AMO sell order {order_id} to MARKET.")  # Debugging print statement
                            except Exception as e:
                                print(f"Error modifying AMO sell order {order_id} to MARKET: {str(e)}")
                    else:
                        try:
                            # Modify the order from LIMIT to MARKET for buy orders and non-AMO sell orders
                            modified_order = kite.modify_order(
                                variety=order['variety'],
                                order_id=order_id,
                                order_type='MARKET'
                            )
                            print(f"Modified order {order_id} from LIMIT to MARKET.")  # Debugging print statement
                        except Exception as e:
                            print(f"Error modifying order {order_id}: {str(e)}")
                            try:
                                # Delete the LIMIT order and place a new MARKET order
                                kite.cancel_order(variety=order['variety'], order_id=order_id)
                                new_order = kite.place_order(
                                    tradingsymbol=order['tradingsymbol'],
                                    exchange=order['exchange'],
                                    transaction_type=order['transaction_type'],
                                    quantity=order['quantity'],
                                    order_type='MARKET',
                                    product=order['product'],
                                    variety=order['variety']
                                )
                                print(f"Deleted order {order_id} and placed new MARKET order {new_order}.")  # Debugging print statement
                            except Exception as e:
                                print(f"Error deleting order {order_id} and placing new MARKET order: {str(e)}")
            else:
                print(f"Order ID not found for order: {order}. Skipping modification.")  # Debugging print statement

    #print(f"open_default_orders after processing: {open_default_orders}")
    open_orders = [order for order in open_orders if 'timestamp' not in order or order['timestamp'] != current_time]

def load_open_default_orders():
    global open_default_orders
    try:
        with open('open_default_orders.json', 'r') as file:
            deserialized_orders = json.load(file)
        print("deserialized_orders in load_open_default_orders", deserialized_orders)
        # Convert string representations back to datetime objects
        open_default_orders = []
        for order in deserialized_orders:
            print("order in for loop", order)
            # Convert string fields back to datetime, if not None
            for key in ['order_timestamp', 'exchange_timestamp']:
                if order[key] is not None:
                    order[key] = datetime.strptime(order[key], '%Y-%m-%d %H:%M:%S')
            open_default_orders.append(order)

        print(f"Loaded default orders from file: {open_default_orders}")  # Debugging print statement
    except FileNotFoundError:
        print("Default orders file not found. Starting with an empty list.")  # Debugging print statement
        open_default_orders = []
    except Exception as e:
        print(f"Error loading default orders from file: {str(e)}")
        open_default_orders = []

def load_default_quantities():
    global default_quantities
    try:
        with open('default_quantities.json', 'r') as file:
            default_quantities = json.load(file)
        print(f"Loaded default quantities from file: {default_quantities}")  # Debugging print statement
    except FileNotFoundError:
        print("Default quantities file not found. Starting with an empty dictionary.")  # Debugging print statement
        default_quantities = {}
    except Exception as e:
        print(f"Error loading default quantities from file: {str(e)}")
        default_quantities = {}

def save_default_quantities():
    global default_quantities
    try:
        with open('default_quantities.json', 'w') as file:
            json.dump(default_quantities, file)
        print(f"Saved default quantities to file: {default_quantities}")  # Debugging print statement
    except Exception as e:
        print(f"Error saving default quantities to file: {str(e)}")

def save_open_default_orders():
    print("inside save_open_default_orders")
    global open_default_orders
    try:
        # Convert datetime objects to string representation
        serializable_orders = []
        for order in open_default_orders:
            #print("order inside for in open_default_orders", order)
            serializable_order = order.copy()
            # Convert all datetime fields to string, if not None
            for key in ['order_timestamp', 'exchange_timestamp']:
                if isinstance(serializable_order[key], datetime):
                    serializable_order[key] = serializable_order[key].strftime('%Y-%m-%d %H:%M:%S')
                elif serializable_order[key] is None:
                    serializable_order[key] = None
            serializable_orders.append(serializable_order)
        #print("Serializable orders:", serializable_orders)
        with open('open_default_orders.json', 'w') as file:
            json.dump(serializable_orders, file)
        print(f"Saved default orders to file: {serializable_orders}")  # Debugging print statement
    except Exception as e:
        print(f"Error saving default orders to file: {str(e)}")

def start_order_check():
        check_and_modify_orders()
        main_window.after(10000, start_order_check)  # Schedule the next call after 10 second

def save_portfolio_on_close():
    global portfolio_name_var
    if not df.equals(original_df):
        portfolio_name = simpledialog.askstring("Save Portfolio", "Enter a name for the portfolio:", initialvalue=portfolio_name_var.get())
        if portfolio_name:
            if portfolio_name == portfolio_name_var.get():
                save_portfolio(portfolio_name)
            else:
                save_portfolio(portfolio_name)
                portfolio_name_var.set(portfolio_name)
            main_window.destroy()  # Close the app after saving
    else:
        main_window.destroy()

def save_portfolio(portfolio_name):
    portfolio_data = df[all_columns].drop(columns=["Check"]).to_dict(orient="records")  # Exclude the "Check" column
    with open(f'{portfolio_name}.json', 'w') as file:
        json.dump(portfolio_data, file)
    messagebox.showinfo("Success", f"Portfolio '{portfolio_name}' saved successfully.")

def load_portfolio(portfolio_name, tree, root):
    global portfolio_name_var
    try:
        tree.delete(*tree.get_children())  # Clear the existing tree
        with open(f'{portfolio_name}.json', 'r') as file:
            portfolio_data = json.load(file)
        for stock in portfolio_data:
            stock["Check"] = "✗"  # Re-add the checkbox column with default value
            add_stock(stock["Exchange"], stock["Symbol"], tree, root, stock)
        messagebox.showinfo("Success", f"Portfolio '{portfolio_name}' loaded successfully.")
        portfolio_name_var.set(portfolio_name)  # Set the portfolio name variable

    except FileNotFoundError:
        messagebox.showerror("Error", f"Portfolio '{portfolio_name}' not found.")

def setup_menu(root, tree):
    menu = tk.Menu(root)
    root.config(menu=menu)
    portfolio_menu = tk.Menu(menu)
    menu.add_cascade(label="Portfolio", menu=portfolio_menu)
    portfolio_menu.add_command(label="Load Portfolio", command=lambda: prompt_load_portfolio(tree, root))
    root.bind('<F4>', lambda event: prompt_load_portfolio(tree, root))

def prompt_load_portfolio(tree, root):
    global portfolio_name_var
    portfolios = [file.split('.json')[0] for file in os.listdir() if file.endswith('.json')]
    portfolios.insert(0, "New Portfolio")  # Add "New Portfolio" as the first option

    portfolio_name = tk.StringVar(value=portfolios[0])
    load_portfolio_window = tk.Toplevel(root)
    load_portfolio_window.title("Load Portfolio")

    ttk.Label(load_portfolio_window, text="Select a portfolio to load:").pack(pady=5)
    portfolio_dropdown = ttk.Combobox(load_portfolio_window, textvariable=portfolio_name, values=portfolios)
    portfolio_dropdown.pack(pady=5)

    def load_selected_portfolio():
        selected_portfolio = portfolio_name.get()
        if selected_portfolio == "New Portfolio":
            # Clear the existing tree and reset the portfolio name variable
            tree.delete(*tree.get_children())
            portfolio_name_var.set("New Portfolio")
        else:
            # Load the selected portfolio
            tree.delete(*tree.get_children())
            load_portfolio(selected_portfolio, tree, root)
        load_portfolio_window.destroy()

    ttk.Button(load_portfolio_window, text="Load", command=load_selected_portfolio).pack(pady=5)

    load_portfolio_window.grab_set()  # Make the dialog box modal
    root.wait_window(load_portfolio_window)  # Wait for the dialog box to be closed

def on_close():
    if df.equals(original_df):
        try:
            main_window.destroy()
        except tk.TclError:
            pass
    else:
        save_portfolio_on_close()  # Save portfolio on app close
        save_open_default_orders()  # Save default orders to file on app shutdown
        try:
            main_window.destroy()
        except tk.TclError:
            pass

if __name__ == "__main__":
    load_open_default_orders()  # Load default orders from file on app startup
    load_default_quantities()
    thread = threading.Thread(target=start_kws)
    thread.start()
    main_window = tk.Tk()
    portfolio_name_var = tk.StringVar(value="New Portfolio")
    configure_style()
    tree = setup_gui(main_window)
    setup_menu(main_window, tree)  # Setup the menu with tree

    #fetch_open_orders()  # Fetch initial open orders
    now = datetime.now().time()
    if time(15,30) > now >= time(8, 20):
        print("inside order time check")
        start_order_check()
        main_window.after(20000, start_order_check)  
    else:
        # Calculate the time until 3:19 PM and schedule the function
        delta = datetime.combine(datetime.today(), time(11, 30)) - datetime.now()
        print("delta date time", delta)
        main_window.after(delta.seconds * 10000, start_order_check)
    main_window.protocol("WM_DELETE_WINDOW", on_close)  # Bind the window close event to on_close function
    main_window.mainloop()
