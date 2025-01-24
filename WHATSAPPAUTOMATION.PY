import os
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from tkinter import Tk, Label, Entry, Button, filedialog, Text, messagebox
from time import sleep
import threading
from twilio.rest import Client
from cryptography.fernet import Fernet
import random 

# File names
activation_data_file = 'activation_data.txt'
key_file = 'encryption_key.key'
twilio_credentials_file = 'twilio_credentials.txt'

def generate_encryption_key():
    key = Fernet.generate_key()
    with open(key_file, 'wb') as f:
        f.write(key)
    return key

def load_encryption_key():
    if os.path.exists(key_file):
        with open(key_file, 'rb') as f:
            key = f.read()
        return key
    else:
        return generate_encryption_key()

def encrypt_file(data, filename):
    key = load_encryption_key()
    cipher_suite = Fernet(key)
    encrypted_data = cipher_suite.encrypt(data.encode())

    with open(filename, 'wb') as f:
        f.write(encrypted_data)

def decrypt_file(filename):
    key = load_encryption_key()
    cipher_suite = Fernet(key)

    with open(filename, 'rb') as f:
        encrypted_data = f.read()

    decrypted_data = cipher_suite.decrypt(encrypted_data)
    return decrypted_data.decode()

def load_twilio_credentials():
    try:
        decrypted_data = decrypt_file(twilio_credentials_file)
        lines = decrypted_data.splitlines()
        if len(lines) < 3:  # Check if there are at least 3 lines
            raise ValueError("Twilio credentials file is not properly formatted.")
        # Return the credentials
        return lines[0].strip(), lines[1].strip(), lines[2].strip()  # SID, Auth Token, WhatsApp Number
    except Exception as e:
        messagebox.showerror("Error", f"Failed to load Twilio credentials: {e}")
        raise

def send_activation_code_via_whatsapp(phone_number, activation_code):
    try:
        TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_NUMBER = load_twilio_credentials()

        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

        # Ensure the phone numbers are in the correct format
        if not TWILIO_WHATSAPP_NUMBER.startswith('whatsapp:'):
            TWILIO_WHATSAPP_NUMBER = 'whatsapp:' + TWILIO_WHATSAPP_NUMBER
        if not phone_number.startswith('whatsapp:'):
            phone_number = 'whatsapp:' + phone_number

        message = client.messages.create(
            body=f"Your activation code is: {activation_code}",
            from_=TWILIO_WHATSAPP_NUMBER,
            to=phone_number
        )
        print(f"Activation code sent to {phone_number}. SID: {message.sid}")
    except Exception as e:
        print(f"Failed to send activation code: {e}")

class ActivationSetup:
    def __init__(self, master):
        self.master = master
        master.title("Setup - First Time User")

        self.dev_name_label = Label(master, text="Developer Name")
        self.dev_name_label.grid(row=0, column=0)
        self.dev_name_entry = Entry(master, width=50)
        self.dev_name_entry.grid(row=0, column=1)

        self.institute_name_label = Label(master, text="Institute Name")
        self.institute_name_label.grid(row=1, column=0)
        self.institute_name_entry = Entry(master, width=50)
        self.institute_name_entry.grid(row=1, column=1)

        self.phone_label = Label(master, text="WhatsApp Phone Number (with country code)")
        self.phone_label.grid(row=2, column=0)
        self.phone_entry = Entry(master, width=50)
        self.phone_entry.grid(row=2, column=1)

        self.activation_code = generate_activation_code()

        self.setup_button = Button(master, text="Save & Send Code", command=self.save_activation_data)
        self.setup_button.grid(row=3, column=1)

    def save_activation_data(self):
        dev_name = self.dev_name_entry.get()
        institute_name = self.institute_name_entry.get()
        phone_number = self.phone_entry.get()

        send_activation_code_via_whatsapp(phone_number, self.activation_code)

        data_to_save = f"{dev_name}\n{institute_name}\n{self.activation_code}"
        encrypt_file(data_to_save, activation_data_file)

        self.master.destroy()

        self.prompt_for_activation_code()

    def prompt_for_activation_code(self):
        activation_window = Tk()
        activation_window.title("Enter Activation Code")

        activation_label = Label(activation_window, text="Enter the activation code sent to your WhatsApp:")
        activation_label.pack()

        self.activation_entry = Entry(activation_window, width=30)
        self.activation_entry.pack()

        activate_button = Button(activation_window, text="Activate", command=lambda: self.check_activation_code(activation_window))
        activate_button.pack()

        activation_window.mainloop()

    def check_activation_code(self, activation_window):
        entered_code = self.activation_entry.get()

        try:
            decrypted_data = decrypt_file(activation_data_file)
            lines = decrypted_data.splitlines()
            correct_code = lines[2].strip()

            if entered_code == correct_code:
                messagebox.showinfo("Success", "Activation Successful!")
                activation_window.destroy()
                launch_whatsapp_sender_app()
            else:
                messagebox.showerror("Error", "Invalid Activation Code! Please try again.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to decrypt activation data: {e}")

class WhatsAppSenderApp:
    def __init__(self, master):
        self.master = master
        master.title("WhatsApp Message Sender")

        self.load_activation_data()

        Label(master, text=f"Developer: {self.dev_name}").grid(row=0, column=0, columnspan=3)
        Label(master, text=f"Institution: {self.institute_name}").grid(row=1, column=0, columnspan=3)

        self.contacts_file_label = Label(master, text="Contacts File")
        self.contacts_file_label.grid(row=2, column=0)

        self.contacts_file_entry = Entry(master, width=50)
        self.contacts_file_entry.grid(row=2, column=1)

        self.browse_button = Button(master, text="Browse", command=self.browse_file)
        self.browse_button.grid(row=2, column=2)

        self.message_label = Label(master, text="Message")
        self.message_label.grid(row=3, column=0)

        self.message_box = Text(master, height=5, width=50)
        self.message_box.grid(row=3, column=1, columnspan=2)

        self.send_button = Button(master, text="Send Messages", command=self.send_messages)
        self.send_button.grid(row=4, column=1, columnspan=2)

        self.reset_button = Button(master, text="Reset Account", command=self.reset_activation)
        self.reset_button.grid(row=5, column=1, columnspan=2)

    def load_activation_data(self):
        try:
            decrypted_data = decrypt_file(activation_data_file)
            lines = decrypted_data.splitlines()
            self.dev_name = lines[0].strip()
            self.institute_name = lines[1].strip()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load activation data: {e}")
            self.master.destroy()

    def browse_file(self):
        filename = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv"), ("Excel files", "*.xlsx")])
        self.contacts_file_entry.insert(0, filename)

    def send_messages(self):
        threading.Thread(target=self.run_sending_process).start()

    def run_sending_process(self):
        contacts_file = self.contacts_file_entry.get()
        message = self.message_box.get("1.0", "end-1c")

        if contacts_file.endswith(".csv"):
            contacts_df = pd.read_csv(contacts_file)
        elif contacts_file.endswith(".xlsx"):
            contacts_df = pd.read_excel(contacts_file)

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service)

        driver.get("https://web.whatsapp.com/")
        sleep(50)

        def send_whatsapp_message(contact_name, contact_number, message):
            try:
                search_box = driver.find_element(By.XPATH, "//div[@contenteditable='true' and @data-tab='3']")
                search_box.clear()
                search_box.click()
                search_box.send_keys(contact_number)
                sleep(2)
                search_box.send_keys(Keys.ENTER)
                sleep(3)

                message_box = driver.find_element(By.XPATH, "//div[@contenteditable='true' and @data-tab='10']")
                message_box.click()
                message_box.send_keys(message)
                message_box.send_keys(Keys.ENTER)
                print(f"Message sent to {contact_name} ({contact_number}).")
            except Exception as e:
                print(f"Failed to send message to {contact_name}: {e}")

        for index, row in contacts_df.iterrows():
            contact_name = row['Name']
            contact_number = row['Phone Number']
            send_whatsapp_message(contact_name, contact_number, message)
            sleep(5)

        driver.quit()
        messagebox.showinfo("Success", "Messages sent successfully!")

    def reset_activation(self):
        if messagebox.askyesno("Reset", "Are you sure you want to reset your account?"):
            if os.path.exists(activation_data_file):
                os.remove(activation_data_file)
                messagebox.showinfo("Reset", "Account has been reset. Please restart the application.")
                self.master.destroy()
def generate_activation_code():
    return str(random.randint(100000, 999999))
def launch_whatsapp_sender_app():
    root = Tk()
    app = WhatsAppSenderApp(root)
    root.mainloop()

if __name__ == "__main__":
    root = Tk()
    app = ActivationSetup(root)
    root.mainloop()
