import telebot
from telebot import types
import sqlite3

TOKEN = "7862415709:AAEwR-lK7h5SGdqcfYJwLt7V3xZ7lpBiVO0"
bot = telebot.TeleBot(TOKEN)

user_requests = {}

def connect_db():
    return sqlite3.connect("trintus_rides.db")

def get_user_phone(message):
    user_id = message.from_user.id
    user_requests[user_id] = {'phone': message.text}
    bot.send_message(message.chat.id, "Please enter your full pickup address (Hotel Name, Room #, Street, City, Zip):")
    bot.register_next_step_handler(message, get_pickup_address)

def get_pickup_address(message):
    user_id = message.from_user.id
    user_requests[user_id]['pickup_address'] = message.text
    bot.send_message(message.chat.id, "Enter your destination address:")
    bot.register_next_step_handler(message, get_destination)

def get_destination(message):
    user_id = message.from_user.id
    user_requests[user_id]['destination'] = message.text
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True)
    markup.add("Standard", "Luxury", "SUV")
    bot.send_message(message.chat.id, "Choose ride type:", reply_markup=markup)
    bot.register_next_step_handler(message, get_ride_type)

def get_ride_type(message):
    user_id = message.from_user.id
    user_requests[user_id]['ride_type'] = message.text
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True)
    markup.add("None", "Armored Vehicle", "Motorized Escort", "Armed Driver")
    bot.send_message(message.chat.id, "Select additional security services (if any):", reply_markup=markup)
    bot.register_next_step_handler(message, get_security_services)

def get_security_services(message):
    user_id = message.from_user.id
    user_requests[user_id]['security_services'] = message.text
    confirm_request(message.chat.id, user_id)

def confirm_request(chat_id, user_id):
    info = user_requests[user_id]
    summary = (f"Ride Request Summary:\n"
               f"📞 Phone: {info['phone']}\n"
               f"📍 Pickup: {info['pickup_address']}\n"
               f"🎯 Destination: {info['destination']}\n"
               f"🚗 Ride Type: {info['ride_type']}\n"
               f"🛡 Security: {info['security_services']}")
    
    markup = types.InlineKeyboardMarkup()
    confirm_button = types.InlineKeyboardButton("Confirm Request", callback_data=f"confirm_{user_id}")
    cancel_button = types.InlineKeyboardButton("Cancel", callback_data=f"cancel_{user_id}")
    markup.add(confirm_button, cancel_button)
    bot.send_message(chat_id, summary, reply_markup=markup)

def save_ride_request(user_id, details):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO ride_requests (user_id, phone, pickup_address, destination, ride_type, security_services, status)
        VALUES (?, ?, ?, ?, ?, ?, 'pending')
    """, (user_id, details['phone'], details['pickup_address'], details['destination'], details['ride_type'], details['security_services']))
    conn.commit()
    conn.close()

def notify_hotel_staff(request_details):
    hotel_chat_id = -100123456789  # Replace with actual group chat ID
    message = (f"🆕 New Ride Request:\n"
               f"📞 Phone: {request_details['phone']}\n"
               f"📍 Pickup: {request_details['pickup_address']}\n"
               f"🎯 Destination: {request_details['destination']}\n"
               f"🚗 Ride Type: {request_details['ride_type']}\n"
               f"🛡 Security: {request_details['security_services']}")
    markup = types.InlineKeyboardMarkup()
    accept_button = types.InlineKeyboardButton("Accept Request", callback_data=f"accept_{request_details['phone']}")
    markup.add(accept_button)
    bot.send_message(hotel_chat_id, message, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_'))
def handle_confirm(call):
    user_id = int(call.data.split('_')[1])
    save_ride_request(user_id, user_requests[user_id])
    notify_hotel_staff(user_requests[user_id])
    bot.send_message(call.message.chat.id, "✅ Your ride request has been submitted!")
    user_requests.pop(user_id, None)
    bot.answer_callback_query(call.id, "Request confirmed!")

@bot.callback_query_handler(func=lambda call: call.data.startswith('cancel_'))
def handle_cancel(call):
    user_id = int(call.data.split('_')[1])
    user_requests.pop(user_id, None)
    bot.send_message(call.message.chat.id, "❌ Ride request cancelled.")
    bot.answer_callback_query(call.id, "Request cancelled.")

try:
    bot.polling(none_stop=True)
except Exception as e:
    print("Error during polling:", e)
