from fasthtml.common import *
from fastlite import *
from fasthtml import ft

db = database("db.sqlite3")
app = FastHTML(pico=True, picocss=True, hdrs=(picolink, Style(':root {--pico-font-size:90%,--pico-font-family: Pacifico, cursive;}')))

class User: 
    name:str 
    email:str
    year_started:int

users = db.create(User, pk='id')
# users.insert(name='Kev Doe', email="kev@kevsrobots.com", year_started=2019)
# users.insert(name='Jane Doe')

# show all users
@app.get("/")
def show_users():
    """ Show all users """
    try:
        all_users = users() # this will show all users - remember its just adding the ()
    except NotFoundError:
        all_users = []
        print("No users found in the database.")
    print(f"All Users: {all_users}")
    return Main(
        H1("Users"),
        ft.Table(
        *[ft.Row(ft.Cell(f"{user.name}"), ft.Cell(f"{user.email}"), ft.Cell(f"{user.year_started}")) for user in all_users],
    ))

serve()