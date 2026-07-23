import os
import pandas as pd
from crud_create import create_log_record
from crud_delete import delete_log_record
from crud_read import read_log_by_component, read_log_records
from crud_update import update_log_level
from db_config import bulk_import_android_csv, init_db

INPUT_FILE_PATH = "Android_2k.log_structured.csv"


def display_menu():
    print("\n=================================")
    print("      LOG RECORD CRUD MENU      ")
    print("=================================")
    print("1. Read Top N Records")
    print("2. Search Records by Component")
    print("3. Create New Log Record")
    print("4. Update Log Level by Line ID")
    print("5. Delete Log Record by Line ID")
    print("6. Exit")
    print("=================================")


def main():
    print("⏳ Initializing SQLite Database...")
    init_db()

    # Import initial CSV into DB if database is empty
    if os.path.exists(INPUT_FILE_PATH):
        bulk_import_android_csv(INPUT_FILE_PATH)
    else:
        print(
            f"⚠️ Warning: '{INPUT_FILE_PATH}' not found. Starting with existing or empty DB."
        )

    while True:
        display_menu()
        choice = input("Enter your choice (1-6): ").strip()

        if choice == "1":
            try:
                n = int(input("Enter number of rows to display: "))
                records = read_log_records(limit=n)
                if records:
                    print("\n", pd.DataFrame(records).to_string(index=False))
                else:
                    print("No records found in database.")
            except ValueError:
                print("Invalid input! Please enter an integer.")

        elif choice == "2":
            component_name = input("Enter Component name to search: ").strip()
            results = read_log_by_component(component_name)
            if results:
                print("\n", pd.DataFrame(results).to_string(index=False))
            else:
                print(f"No records found for Component: {component_name}")

        elif choice == "3":
            print("\n--- Create New Log Record ---")
            try:
                date_val = input("Enter Date (e.g., 170323): ").strip()
                time_val = input("Enter Time (e.g., 12:00:00.000): ").strip()
                pid = int(input("Enter PID: "))
                tid = int(input("Enter TID: "))
                level = (
                    input(
                        "Enter Level (V=Verbose, D=Debug, I=Info, W=Warn, E=Error, F=Fatal): "
                    )
                    .strip()
                    .upper()
                )
                component = input("Enter Component: ").strip()
                content = input("Enter Content/Message: ").strip()

                # Saves to DB -> Auto-syncs to exported_logs.csv
                create_log_record(
                    date_val, time_val, pid, tid, level, component, content
                )
            except ValueError:
                print("Invalid input format! PID and TID must be integers.")

        elif choice == "4":
            print("\n--- Update Log Level ---")
            try:
                line_id = int(input("Enter Line ID to update: "))
                new_level = (
                    input("Enter new Level (V, D, I, W, E, F): ")
                    .strip()
                    .upper()
                )
                update_log_level(line_id=line_id, new_level=new_level)
            except ValueError:
                print("Invalid Line ID input!")

        elif choice == "5":
            print("\n--- Delete Log Record ---")
            try:
                line_id = int(input("Enter Line ID to delete: "))
                delete_log_record(line_id=line_id)
            except ValueError:
                print("Invalid Line ID input!")

        elif choice == "6":
            print(
                "\nExiting program. All database changes have been saved and exported to CSV. Goodbye!"
            )
            break

        else:
            print("Invalid choice! Please enter a number from 1 to 6.")


if __name__ == "__main__":
    main()