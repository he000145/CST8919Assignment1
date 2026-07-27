# CST8919 Lab 1 - Flask Authentication with Auth0

## Overview

This project is integrated Auth0 authentication into a Flask web application. Users can securely log in and log out using Auth0, and authenticated users can access a protected page.

## Features

* User Login with Auth0
* User Logout with Auth0
* User Profile Page
* Protected Route (`/protected`)
* Redirect unauthenticated users to the login page

## Technologies Used

* Python
* Flask
* Auth0
* HTML/CSS

## Auth0 Configuration

Create a Regular Web Application in Auth0 and configure the following URLs:

### Allowed Callback URLs

http://localhost:5000/callback

### Allowed Logout URLs

http://localhost:5000

### Allowed Web Origins

http://localhost:5000

## Environment Variables

Create a `.env` file in the project root directory:

```env
# Auth0 Configuration
AUTH0_DOMAIN=YOUR_AUTH0_DOMAIN
AUTH0_CLIENT_ID=YOUR_CLIENT_ID
AUTH0_CLIENT_SECRET=YOUR_CLIENT_SECRET
AUTH0_SECRET=YOUR_GENERATED_SECRET
AUTH0_REDIRECT_URI=http://localhost:5000/callback
```

## Installation

Create and activate a virtual environment:

```bash
python -m venv venv
```

Windows:

```bash
venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Run the Application

```bash
python app.py
```

The application will be available at:

```text
http://localhost:5000
```

## Protected Route

The application includes a protected page:

```text
http://localhost:5000/protected
```

Authenticated users can access the page. Unauthenticated users will be redirected to the login page.

## Demo Video

YouTube Link:

[[Lab Youtube Link](https://youtu.be/kS2AiAfKSmU)]
