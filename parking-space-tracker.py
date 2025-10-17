from google.cloud import firestore
from google.cloud.firestore_v1 import aggregation
from google.cloud.firestore_v1.base_query import FieldFilter
from typing import Optional
import traceback


db = firestore.Client()

def get_space_by_name(db: firestore.Client, name: str):
    space_doc = (db.collection("spaces").where(filter=FieldFilter("name", "==", name)).stream())
    
    did_the_loop_run = 0
    for doc in space_doc:
        did_the_loop_run = 1
        print(f"{doc.id} => {doc.to_dict()}")
        return doc.id

    if did_the_loop_run == 0:
        print("nothing returned")


# This function allows the user to create a parking space. It takes the name and
# occupancy status as parameters and returns a string.
def add_space(db, name: str, occupied: bool) -> str:
    document_reference = db.collection("spaces").document()
    document_reference.set({ "name": name, "occupied": occupied })
    # return the ID so we know that adding was successful
    return document_reference.id

def update_space(db: firestore.Client, current_name: str, new_name: Optional[str] = None, new_occupancy_state: Optional[bool] = None):
    # find the space by the current name (unique)
    snap = next(db.collection("spaces").where(filter=FieldFilter("name", "==", current_name)).limit(1).stream(), None)

    if snap is None:
        print(f"No space found with name: {current_name!r}")
        return
    
    # If we're renaming make sure the spot name is not already used
    if new_name is not None and new_name != current_name:
        # search for a duplicate and set to None if not found
        duplicate = next(db.collection("spaces").where(filter=FieldFilter("name", "==", new_name)).limit(1).stream(), None)

        if duplicate is not None: 
            print(f"Another space already uses the name {new_name!r}.")
            return
    
    updates = {}
    # decide what to update and add it to a dictionary that will be pushed 
    if new_name is not None:
        updates["name"] = new_name
    if new_occupancy_state is not None:
        updates["occupied"] = bool(new_occupancy_state)
    snap.reference.update(updates)
    print(f"Updated space! ")





def delete_space(d: firestore.Client, name: str): 
    # Delete a space by its unique name. Returns True if deleted, False if not found.
    snap = next(db.collection("spaces").where(filter=FieldFilter("name", "==", name)).limit(1).stream(), None )
    if snap is None:
        print(f"No space found with name: {name!r}")
        return False

    # delete the space
    snap.reference.delete()
    print(f"Deleted space '{name}' (id={snap.id})")

def read_all_spaces(db: firestore.Client):
    found_spaces = False
    document_reference = db.collection("spaces")
    spaces_docs = document_reference.stream()

    spaces_formatted = ""
    for doc in spaces_docs:
        space_dict = doc.to_dict()
        spaces_formatted += str(space_dict.get("name")) + ": "
        spaces_formatted += "Full\n" if space_dict.get("occupied") == True else "Empty\n"
    return spaces_formatted


    
def example_code():
    doc_ref = db.collection("users").document("alovelace")
    doc_ref.set({"first" : "Ada", "last": "Lovelace", "born": 1815})

    doc_ref = db.collection("users").document("aturing")
    doc_ref.set({"first": "Alan", "middle": "Mathison", "last": "Turing", "born": 1912})

    users_ref = db.collection("users")
    docs = users_ref.stream()

    for doc in docs:
        print(f"{doc.id} => {doc.to_dict()}")

def main():
    print("\n\nWelcome to the parking spaces tracker! ")
    print("\nMenu: ")
    print("1: See all spaces ")
    print("2: Add a space")
    print("3. Update a space")
    print("4. Remove a space")
    print("5. Exit")
    
    while True:
        try:
            user_choice = int(input("Please select an option: "))
            if user_choice == 1:
                spaces_str = read_all_spaces(db)
                print(spaces_str)
                # See all the spaces 
            
            # add a space 
            elif user_choice == 2:
                spot_name = input("Parking spot nickname: ")

                query_reference = db.collection("spaces")
                query = query_reference.where(filter=FieldFilter("name", "==", spot_name))
                aggregate_query = aggregation.AggregationQuery(query)
                
                aggregate_query.count(alias="all")
                results = aggregate_query.get()
                query_hits = 0
                for result in results:
                    query_hits = result[0].value
                if query_hits > 0:
                    raise Exception("Spot names must be unique.")

                spot_occupancy_str = input("Is the spot (e)mpty or (f)ull? (e/f): ")
                spot_occupancy_bool = True

                if spot_occupancy_str == "f":
                    pass
                elif spot_occupancy_str == "e":
                    spot_occupancy_bool = False
                else:
                    raise Exception
                
                

                spot_id = add_space(db, spot_name, spot_occupancy_bool)
                if len(spot_id) > 5:
                    print("Spot added successfully!")
                else: 
                    print("Something went wrong. The spot could not be added")

            # update a space 
            elif user_choice == 3:
                print("Here is the list of spaces: \n")
                print(read_all_spaces(db))
                
                current = input("Type the name of the space that you want to update: ").strip()
                choice = input("Update (n)ame, (o)ccupancy, or (b)oth? [n/o/b]: ").strip().lower()

                new_name = None
                new_occupancy = None 

                if choice in ("n", "b"):
                    new_name = input("New nickname: ").strip()
                    # make sure the new name is unique
                    if new_name and new_name != current:
                        # search for a duplicate name, and set duplicate to None if there isn't one
                        duplicate = next(db.collection("spaces").where(filter=FieldFilter("name", "==", new_name)).limit(1).stream(), None)
                    if duplicate is not None:
                        print("That name is already in use.")
                        continue
                    
                if choice in ("o", "b"):
                    occupancy = input("Is the spot (e)mpty or (f)ull? (e/f): ").strip().lower()
                    if occupancy not in ("e", "f"):
                        print("Please enter 'e' or 'f'")
                        continue
                    # nice easy direct boolean
                    new_occupancy = (occupancy == "f")
                
                update_space(db, current_name=current, new_name=new_name, new_occupancy_state=new_occupancy)
                    

            # delete a space
            elif user_choice == 4:
                # Delete a space
                print("Here is the list of spaces: ")
                print(read_all_spaces(db))

                target = input("Type the name of the space to delete: ").strip()
                if not target:
                    print("Please enter a name.")
                    continue

                confirm = input(f"Are you sure you want to delete '{target}'? (y/N): ").strip().lower()
                if confirm not in ("y", "yes"):
                    print("Space deletion cancelled.")
                    continue

                delete_space(db, target)
            elif user_choice == 5:
                exit()
            else:
                raise Exception
        except Exception as e:
            print("Please enter a valid option/data. ")
            print(f"{e}")
            traceback.print_exc()
            



if __name__ == "__main__":
    main()