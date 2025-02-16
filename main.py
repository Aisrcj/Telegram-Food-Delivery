import telebot
from telebot import types
import os
import sqlite3

bot_token = '7862415709:AAEwR-lK7h5SGdqcfYJwLt7V3xZ7lpBiVO0' #From BotFather in Telegram
bot = telebot.TeleBot(bot_token)

user_info = {}
order_counter = 1


def connect_db():
    try:
        conn = sqlite3.connect('bot_database.db')
        return conn
    except Exception as e:
        print(f"Database connection failed: {e}")
        return None


def create_tables():
    conn = connect_db()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                ticket_number TEXT PRIMARY KEY,
                client_chat_id INTEGER,
                manager_chat_id INTEGER,
                order_status TEXT DEFAULT 'pending',
                paid BOOLEAN DEFAULT FALSE,
                restaurant TEXT,
                name TEXT,
                phone TEXT,
                address TEXT,
                delivery_method TEXT DEFAULT 'pickup' -- Add the delivery_method column
            )""")
            conn.commit()
            print("Tables created successfully.")
        except Exception as e:
            print(f"Failed to create tables: {e}")
        finally:
            conn.close()


def check_table_columns():
    conn = connect_db()
    try:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(orders)")
        columns = cursor.fetchall()
        print(columns)  # This will show all columns in the orders table
    except Exception as e:
        print(f"Failed to fetch table structure: {e}")
    finally:
        conn.close()


def add_missing_columns():
    conn = connect_db()
    try:
        cursor = conn.cursor()
        # Add restaurant column if missing
        cursor.execute("ALTER TABLE orders ADD COLUMN restaurant TEXT")
        # Add other missing columns
        cursor.execute("ALTER TABLE orders ADD COLUMN name TEXT")
        cursor.execute("ALTER TABLE orders ADD COLUMN phone TEXT")
        cursor.execute("ALTER TABLE orders ADD COLUMN address TEXT")
        cursor.execute("ALTER TABLE orders ADD COLUMN delivery_method TEXT DEFAULT 'pickup'")
        conn.commit()
        print("Missing columns added successfully.")
    except sqlite3.OperationalError as e:
        print(f"Column already exists: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        conn.close()


create_tables()  # Ensure the database and tables are created
add_missing_columns()  # Ensure missing columns are added


restaurants = [
    "🍔 Five Guys", "🌯 Chipotle", "🍕 Pizza",
    "🍜 Panda Express", "🍗 Wingstop", "🥩 Texas Road House",
    "🍦 Dairy Queen", "🌮 Qdoba", "🍔 Sonic Drive"
]


restaurant_data = {
    "🍔 Five Guys": {
        "photo": "Five Guys.jpeg",
        "text": """🍔 45% OFF
🍔 $40 Min Cart
🍔 Pickup & Delivery"""
    },
    "🌯 Chipotle": {
        "photo": "Chipotle.jpeg",
        "text": """🌯 50% OFF
🌯 $40 Min total cart
🌯 Delivery & Pickup"""
    },
    "🍕 Pizza": {
        "photo": "Pizza.jpeg",
        "text": """🍕Dominos, Pizza Hut, Papa John's

🍕50% OFF
🍕$40 Min total cart
🍕Delivery & Pickup"""
    },
    "🍜 Panda Express": {
        "photo": "Panda Express.jpeg",
        "text": """50% OFF
$40 Min total cart
Delivery & Pickup"""
    },
    "🍗 Wingstop": {
        "photo": "Wing Stop.jpeg",
        "text": """
🍗 50% OFF
🍗 $45 Min total cart
🍗 Delivery & Pickup"""
    },
    "🥩 Texas Road House": {
        "photo": "Texas.jpeg",
        "text": """🥩 45% OFF
🥩 $40 Min total cart
🥩 Pickup Only"""
    },
    "🍦 Dairy Queen": {
        "photo": "DQ.jpeg",
        "text": """🍦 50% OFF
🍦 $40 Min total cart
🍦 Pickup & Delivery"""
    },
    "🌮 Qdoba": {
        "photo": "Qdoba.jpeg",
        "text": """Qdoba

🌮 50% OFF
🌮 $40 Min total cart
🌮 Pickup only"""
    },
    "🍔 Sonic Drive": {
        "photo": "Sonic.jpeg",
        "text": """🍔 60% OFF
🍔 $40 Min total cart
🍔 Pickup & Delivery"""
    }
}


@bot.message_handler(commands=['start', 'order'])
def start_order(message):
    try:
        with open('Logo.jpeg', 'rb') as photo:
            bot.send_photo(message.chat.id, photo=photo, caption="Welcome to Stratton Oakmont Eats!")
        markup = types.InlineKeyboardMarkup(row_width=2)
        buttons = [types.InlineKeyboardButton(text=rest, callback_data=rest) for rest in [
            "🍔 Five Guys", "🌯 Chipotle", "🍕 Pizza", "🍜 Panda Express", "🍗 Wingstop",
            "🥩 Texas Road House", "🍦 Dairy Queen", "🌮 Qdoba", "🍔 Sonic Drive"]]
        markup.add(*buttons)
        bot.send_message(message.chat.id, 'Please choose a restaurant:', reply_markup=markup)
    except Exception as e:
        print("Failed to start order:", e)
        bot.reply_to(message, "Failed to start order due to an internal error.")


@bot.message_handler(commands=['cancel'])
def cancel_order(message):
    user_id = message.from_user.id
    # Check if the user has information stored in user_info
    if user_id in user_info:
        order_details = user_info[user_id]
        if order_details and 'order_number' in order_details:
            # Cancel the order in the database
            cancel_order_in_database(order_details['order_number'])

            # Notify the manager if they have been assigned
            if 'manager_chat_id' in order_details and order_details['manager_chat_id']:
                bot.send_message(order_details['manager_chat_id'],
                                 f"Order #{order_details['order_number']} has been canceled by the client.")

            # Send cancellation to the group channel if necessary
            manager_group_chat_id = -1002017593444  # Example group ID
            bot.send_message(manager_group_chat_id, f"Order #{order_details['order_number']} canceled by client.")

            # Notify the client of the cancellation
            bot.send_message(user_id, "Your order has been canceled. Thank you for using our service.")

            # Remove the order from user_info
            del user_info[user_id]
        else:
            bot.send_message(message.chat.id, "No active order found to cancel.")
    else:
        bot.send_message(message.chat.id, "You don't have an active order to cancel.")


def update_database_schema_with_delivery_mode():
    conn = connect_db()
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE orders ADD COLUMN delivery_mode TEXT")
        conn.commit()
        print("Delivery mode column added successfully.")
    except sqlite3.OperationalError as e:
        print(f"Column already exists: {e}")
    finally:
        conn.close()


update_database_schema_with_delivery_mode()


# Telegram Bot Callback Handlers
@bot.callback_query_handler(func=lambda call: call.data.startswith('paid_'))
def handle_payment_confirmation(call):
    try:
        # Extract the ticket number from callback data if needed (optional for now)
        ticket_number = call.data.split('_')[1]

        # Assume the original message text is directly accessible via `call.message.text`
        if call.message.text:
            paid_message = f"{call.message.text}\n✅ Paid"
            bot.send_message(call.message.chat.id, paid_message)
            bot.answer_callback_query(call.id, "Order marked as paid!", show_alert=True)
        else:
            bot.answer_callback_query(call.id, "Failed to retrieve order details.", show_alert=True)
    except Exception as e:
        print(f"Error handling payment confirmation: {e}")
        bot.answer_callback_query(call.id, "An error occurred while processing.", show_alert=True)


def get_order_details_by_client_id(client_chat_id):
    conn = connect_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT ticket_number, manager_chat_id, name, phone FROM orders WHERE client_chat_id = ? AND order_status = 'pending'", (client_chat_id,))
        result = cursor.fetchone()
        return {
            'ticket_number': result[0],
            'manager_chat_id': result[1],
            'name': result[2],
            'phone': result[3]
        } if result else None
    finally:
        cursor.close()
        conn.close()


def cancel_order_in_database(ticket_number):
    conn = connect_db()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE orders SET order_status = 'canceled' WHERE ticket_number = ?", (ticket_number,))
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def resend_message(chat_id, message, sender_type):
    # Determine the prefix based on who is sending the message
    if sender_type == "client":
        prefix = "<b>Client:</b> "  # For client view, it shows "Manager:"
    else:
        prefix = "<b>Manager:</b> "    # For manager view, it shows "Client:"

    # Check the message type to handle text, photos, etc., and prepend the prefix
    if message.text:
        bot.send_message(chat_id, f"{prefix}{message.text}", parse_mode='HTML')
    elif message.photo:
        photo = message.photo[-1].file_id
        caption = f"{prefix}{message.caption}" if message.caption else prefix.strip()
        bot.send_photo(chat_id, photo, caption=caption, parse_mode='HTML')
    elif message.audio:
        bot.send_audio(chat_id, message.audio.file_id, caption=prefix.strip(), parse_mode='HTML')
    elif message.document:
        bot.send_document(chat_id, message.document.file_id, caption=prefix.strip(), parse_mode='HTML')
    elif message.voice:
        bot.send_voice(chat_id, message.voice.file_id, caption=prefix.strip(), parse_mode='HTML')
    elif message.video:
        bot.send_video(chat_id, message.video.file_id, caption=prefix.strip(), parse_mode='HTML')
    else:
        bot.send_message(chat_id, f"{prefix}Received an unsupported message type.", parse_mode='HTML')


def order_already_accepted(ticket_number):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT manager_chat_id FROM orders WHERE ticket_number = ?", (ticket_number,))
    result = cursor.fetchone()
    conn.close()
    return result is not None and result[0] is not None


def mark_order_as_accepted(ticket_number, manager_id):
    conn = connect_db()
    cursor = conn.cursor()
    try:
        # Ensure this query is correct and actually updates the record as expected
        cursor.execute("UPDATE orders SET manager_chat_id = ?, order_status = 'accepted' WHERE ticket_number = ?", (manager_id, ticket_number))
        conn.commit()
    except Exception as e:
        print(f"Failed to update order acceptance: {e}")
    finally:
        cursor.close()
        conn.close()


def retrieve_client_chat_id(ticket_number):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT client_chat_id FROM orders WHERE ticket_number = ?", (ticket_number,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None


create_tables()  # Ensure the database and tables are created


@bot.callback_query_handler(func=lambda call: call.data.startswith('accept_'))
def handle_order_acceptance(call):
    ticket_number = call.data.split('_')[1]
    if order_already_accepted(ticket_number):
        bot.answer_callback_query(call.id, "This order has already been accepted by another manager.", show_alert=True)
    else:
        mark_order_as_accepted(ticket_number, call.from_user.id)
        client_chat_id = retrieve_client_chat_id(ticket_number)
        if client_chat_id:
            bot.send_message(call.from_user.id, "You have accepted the order. You can now chat with the client.")
            bot.send_message(client_chat_id, "Your order has been accepted by a manager. You can chat here now.")
        else:
            bot.send_message(call.from_user.id, "Failed to retrieve client details.")


def retrieve_all_manager_chat_ids():
    """Retrieve a list of all manager chat IDs from the database."""
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT manager_chat_id FROM orders WHERE order_status = 'accepted'")
    manager_ids = cursor.fetchall()
    conn.close()
    return [mid[0] for mid in manager_ids]


def retrieve_all_client_chat_ids():
    """Retrieve a list of all client chat IDs from the database."""
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT client_chat_id FROM orders WHERE order_status = 'accepted'")
    client_ids = cursor.fetchall()
    conn.close()
    return [cid[0] for cid in client_ids]


def find_client_for_manager(manager_chat_id):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT client_chat_id FROM orders WHERE manager_chat_id = ?", (manager_chat_id,))
    client_id = cursor.fetchone()
    conn.close()
    return client_id[0] if client_id else None


def find_manager_for_client(client_chat_id):
    conn = connect_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT manager_chat_id FROM orders WHERE client_chat_id = ? AND order_status = 'accepted'", (client_chat_id,))
        manager_id = cursor.fetchone()
        if manager_id:
            return manager_id[0]
        else:
            print(f"No manager found for client ID {client_chat_id}")
    except Exception as e:
        print(f"Database query error: {e}")
    finally:
        cursor.close()
        conn.close()
    return None


@bot.message_handler(content_types=['text', 'photo'])
def handle_communication(message):
    # Determine if the message sender is a manager or a client
    if message.chat.id in retrieve_all_manager_chat_ids():
        # The sender is a manager
        client_chat_id = find_client_for_manager(message.chat.id)
        if client_chat_id:
            resend_message(client_chat_id, message, "manager")
    elif message.chat.id in retrieve_all_client_chat_ids():
        # The sender is a client
        manager_chat_id = find_manager_for_client(message.chat.id)
        if manager_chat_id:
            resend_message(manager_chat_id, message, "client")

def resend_message(chat_id, message, sender_type):
    # Prepare the prefix based on who is sending the message
    prefix = "<b>Manager:</b> " if sender_type == "manager" else "<b>Client:</b> "

    # Handle different types of messages
    if message.content_type == 'text':
        bot.send_message(chat_id, f"{prefix}{message.text}", parse_mode='HTML')
    elif message.content_type == 'photo':
        photo = message.photo[-1].file_id  # Sending the highest resolution photo
        caption = f"{prefix}{message.caption}" if message.caption else prefix.strip()
        bot.send_photo(chat_id, photo, caption=caption, parse_mode='HTML')


def generate_order_number():
    conn = connect_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT MAX(CAST(ticket_number AS INTEGER)) FROM orders")
        max_number = cursor.fetchone()[0]
        next_order_number = int(max_number) + 1 if max_number is not None else 1
    except Exception as e:
        print(f"Error fetching max ticket_number: {e}")
        next_order_number = 1
    finally:
        cursor.close()
        conn.close()
    return str(next_order_number)  # Convert to string for consistent handling


@bot.callback_query_handler(func=lambda call: call.data in [
    "Five Guys", "Chipotle", "Pizza Hut", "Panda Express", "Wingstop",
    "Texas Road House", "Dairy Queen", "Qdoba", "Sonic Drive"])


@bot.callback_query_handler(func=lambda call: call.data in restaurants)
def handle_query(call):
    user_id = call.from_user.id
    restaurant = call.data
    if restaurant in restaurant_data:
        # Retrieve the photo and text for the selected restaurant
        photo_path = restaurant_data[restaurant]["photo"]
        message_text = restaurant_data[restaurant]["text"]

        # Update the user info with selected restaurant and generate order number
        user_info[user_id] = {
            'restaurant': restaurant,
            'order_number': generate_order_number()
        }

        # Answer the callback query
        bot.answer_callback_query(call.id)

        # Send the specific restaurant photo and text
        with open(photo_path, 'rb') as photo:
            bot.send_photo(call.message.chat.id, photo=photo, caption=message_text)

        # Follow up with asking for the user's name
        bot.send_message(call.message.chat.id, "Please provide your name.")
        bot.register_next_step_handler_by_chat_id(call.message.chat.id, get_user_name)
    else:
        bot.answer_callback_query(call.id, "Selection not recognized, please try again.")


def get_user_name(message):
    user_id = message.from_user.id
    user_info[user_id]['name'] = message.text
    bot.send_message(message.chat.id, "Thank you! Please enter your phone number.")
    bot.register_next_step_handler_by_chat_id(message.chat.id, get_user_phone)


def get_user_phone(message):
    user_id = message.from_user.id
    user_info[user_id]['phone'] = message.text
    bot.send_message(message.chat.id, "Please enter your full delivery address (must include apt#, zip, state , etc format example : 4455 Landing Lange, APT 4 , Louisville, KY 40018:")
    bot.register_next_step_handler_by_chat_id(message.chat.id, get_user_address)


def get_user_address(message):
    user_id = message.from_user.id
    user_info[user_id]['address'] = message.text
    markup = types.InlineKeyboardMarkup()
    pickup_button = types.InlineKeyboardButton("Pickup", callback_data="pickup")
    delivery_button = types.InlineKeyboardButton("Delivery", callback_data="delivery")
    markup.add(pickup_button, delivery_button)
    bot.send_message(message.chat.id, "Please select delivery mode:", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == "pickup" or call.data == "delivery")
def handle_delivery_mode_selection(call):
    user_id = call.from_user.id
    user_info[user_id]['delivery_mode'] = call.data
    compile_and_send_order_summary(call.message.chat.id, user_id)
    bot.answer_callback_query(call.id, f"{call.data.capitalize()} mode selected!")


def get_delivery_method(message, user_id):
    delivery_method = message.text
    user_info[user_id]['delivery_method'] = delivery_method
    compile_and_send_order_summary(message.chat.id, user_id)


def save_order_details(user_id, details):
    conn = connect_db()
    cursor = conn.cursor()
    # Using parameterized queries to safely insert data
    cursor.execute("""
        INSERT INTO orders (ticket_number, client_chat_id, order_status) VALUES (?, ?, 'pending')
        ON CONFLICT(ticket_number) DO UPDATE SET
        client_chat_id = excluded.client_chat_id,
        order_status = excluded.order_status;
    """, (details['order_number'], user_id))  # details['order_number'] is already a string
    conn.commit()
    conn.close()


def compile_and_send_order_summary(chat_id, user_id):
    info = user_info[user_id]
    summary = (
        f"Order Summary:\n"
        f"Order Number: #{info['order_number']}\n"
        f"Restaurant: {info['restaurant']}\n"
        f"Name: {info['name']}\n"
        f"Phone Number: {info['phone']}\n"
        f"Address: {info['address']}\n"
        f"Delivery Mode: {info['delivery_mode'].capitalize()}\n"
    )
    save_order_details(user_id, info)
    bot.send_message(chat_id, summary)

    # Ensure the correct keys are used here:
    notify_managers({
        'ticket_number': info['order_number'],  # Ensure this is the correct identifier
        'client_chat_id': chat_id,
        'restaurant': info['restaurant'],
        'name': info['name'],
        'phone': info['phone'],
        'address': info['address'],
        'delivery_mode': info['delivery_mode']
    })


def notify_managers(order_details):
    conn = connect_db()
    try:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO orders (ticket_number, client_chat_id, manager_chat_id, order_status, delivery_mode)
        VALUES (?, ?, NULL, 'pending', ?)
        ON CONFLICT(ticket_number) DO UPDATE SET
            client_chat_id = excluded.client_chat_id,
            manager_chat_id = NULL,
            order_status = 'pending',
            delivery_mode = excluded.delivery_mode;
        """, (order_details['ticket_number'], order_details['client_chat_id'], order_details['delivery_mode']))
        conn.commit()

        order_message = (f"🆕 New Order: #{order_details['ticket_number']}\n"
                         f"🍴 Restaurant: {order_details['restaurant']}\n"
                         f"👤 Name: {order_details['name']}\n"
                         f"📞 Phone: {order_details['phone']}\n"
                         f"📍 Address: {order_details['address']}\n"
                         f"📦 Delivery Mode: {order_details['delivery_mode'].capitalize()}\n")
        markup = types.InlineKeyboardMarkup()
        accept_button = types.InlineKeyboardButton("Accept the Order", callback_data=f"accept_{order_details['ticket_number']}")
        paid_button = types.InlineKeyboardButton("Mark as Paid", callback_data=f"paid_{order_details['ticket_number']}")
        markup.add(accept_button, paid_button)
        manager_group_chat_id = -1002017593444  # This should be set to your actual group chat ID
        bot.send_message(manager_group_chat_id, order_message, reply_markup=markup)
    except Exception as e:
        print(f"Failed to notify managers due to: {e}")
    finally:
        conn.close()


def confirm_order(chat_id, user_id):
    info = user_info[user_id]
    markup = types.InlineKeyboardMarkup()
    confirm_button = types.InlineKeyboardButton("Confirm Order", callback_data=f"confirm_{user_id}")
    cancel_button = types.InlineKeyboardButton("Cancel Order", callback_data=f"cancel_{user_id}")
    markup.add(confirm_button, cancel_button)
    summary = (
        f"Please confirm your order details:\n"
        f"Restaurant: {info['restaurant']}\n"
        f"Name: {info['name']}\n"
        f"Phone: {info['phone']}\n"
        f"Address: {info['address']}\n"
    )
    bot.send_message(chat_id, summary, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_'))
def handle_order_confirmation(call):
    user_id = int(call.data.split('_')[1])
    if user_id in user_info:
        finalize_order(call.message.chat.id, user_id)
        bot.answer_callback_query(call.id, "Order confirmed!")
    else:
        bot.answer_callback_query(call.id, "No active order found.", show_alert=True)


@bot.callback_query_handler(func=lambda call: call.data.startswith('cancel_'))
def handle_order_cancellation(call):
    user_id = int(call.data.split('_')[1])
    if user_id in user_info:
        user_info.pop(user_id, None)
        bot.send_message(call.message.chat.id, "Order cancelled successfully.")
        bot.answer_callback_query(call.id, "Order cancelled.")
    else:
        bot.answer_callback_query(call.id, "No active order to cancel.", show_alert=True)


def finalize_order(chat_id, user_id):
    info = user_info[user_id]
    # Save the confirmed order to the database
    save_order_details(user_id, info)
    # Optionally, notify managers about the new order here
    notify_managers({
        'ticket_number': info['order_number'],
        'client_chat_id': chat_id
    })
    bot.send_message(chat_id, "Your order has been placed and is being processed. You will be notified once a manager accepts your order.")
    user_info.pop(user_id, None)  # Clear user info after finalizing the order


try:
    bot.polling(none_stop=True)
except Exception as e:
    print("There is definitely an error when polling: ", e)
