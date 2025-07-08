# Country Game Database

A web application for managing data from the Country Game using Flask and MySQL.

## Prerequisites

- Python 3.6 or higher
- MySQL Server
- pip (Python package manager)

## Installation

1. Clone this repository or download the source code.

2. Install the required Python packages:
   ```
   pip install -r requirements.txt
   ```

3. Make sure MySQL server is running and accessible with the following credentials:
   - Username: `root`
   - Password: `Beholder30`
   - Host: `localhost`

## Database Setup

1. Run the database setup script to create the database and import data from the CSV files:
   ```
   python db_setup.py
   ```

   This script will:
   - Create a database named `county_game_server`
   - Create tables for stats, resources, actions, and projects
   - Import data from the CSV files into these tables

## Running the Application

1. Start the Flask application:
   ```
   python app.py
   ```

2. Open a web browser and navigate to:
   ```
   http://localhost:5000
   ```

## Usage

The application provides a web interface for managing the following data:

### Stats
- View all character stats (Politics, Military, Economics, etc.)
- Add new stats
- Edit existing stats
- Delete stats

### Resources
- View all game resources (Coal, Iron, Crops, etc.)
- Add new resources
- Edit existing resources
- Delete resources

### Actions
- View all player actions
- Add new actions
- Edit existing actions
- Delete actions

### Projects
- View all ongoing projects
- Add new projects
- Edit existing projects
- Delete projects

## Data Structure

The application uses the following database structure:

### Stats Table
- id: Primary key
- name: Name of the stat
- rating: Numeric rating
- modifier: Optional modifier
- notes: Optional notes
- advisor: Optional advisor name

### Resources Table
- id: Primary key
- name: Name of the resource
- type: Type of resource (Food, Lux, Strat, etc.)
- tier: Tier level
- natively_produced: Amount natively produced
- trade: Amount from trade
- committed: Amount committed
- not_developed: Amount not developed
- available: Amount available

### Actions Table
- id: Primary key
- action_number: Action number
- description: Description of the action
- stat1: First stat used
- stat1_value: Value of first stat
- stat2: Second stat used
- stat2_value: Value of second stat
- advisor_used: Whether an advisor was used
- resources_used: Resources used for the action
- gold_spent: Amount of gold spent

### Projects Table
- id: Primary key
- name: Name of the project
- effect: Effect of the project
- cost: Cost in gold
- resources: Resources required
- status: Status (O: Ongoing, U: Unfinished, S: Suspended)
- progress_per_turn: Progress made per turn
- total_needed: Total progress needed
- total_progress: Current progress
- turn_started: Turn when the project started
