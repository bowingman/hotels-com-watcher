# HOTELS-COM-WATCHER

This project aims to develop a hotel room surveillance system using Selenium and Streamlit technologies. The primary domain for this project is https://www.hilton.com/. The system is designed to monitor hotel room availability and send notifications to the user via email.

## Environment Configuration

### **To configure the system, the following parameters are required:**

- `user_mail_address` : This should be the email address of the user. This email address will be used as the sender when sending notifications.
- `mail_app_key` : This is the key required to access the user's email address and send notifications.
- `hostname` : This parameter is required to connect to the database.
- `username` : This parameter is required to access the database.
- `password` : This parameter is required to access the database.
- `database` : This parameter is required to connect to the database.
- `base_url` : This parameter is used to crawl data from the primary domain.

## HOW TO RUN

```
pip install -r requirements.txt

streamlit run hotels-com-watcher.py
```

## Workflow

### **The system is designed to validate the data entered by the user to ensure its accuracy. The following validation rules are applied:**

- `Arrival Date Validation` : The arrival date must be greater than the current date.

- `Departure Date Validation` : The departure date must be less than the arrival date + 14 days.

- `Notification Expiration` : If the arrival date is greater than the current date, the notification will be considered expired.

**Note: The system is designed to allow only one notification per email address. If a notification has already been set for a particular email address, the user can only update or delete the existing notification.**

## Technical Stack

### **The following technologies are used in this project:**

- `Selenium` : This is an open-source framework used for automating web browsers. It is used to crawl data from the primary domain.

- `Streamlit` : This is an open-source framework used to build data-driven applications. It is used to display the results of the data crawled by Selenium.
