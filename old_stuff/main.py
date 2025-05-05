from fasthtml.common import * 

from passlib.context import CryptContext

from functools import wraps
from datetime import datetime

custom_styles = Style("""
.mw-960 { max-width: 960px; }
.mw-480 { max-width: 480px; }
.mx-auto { margin-left: auto; margin-right: auto; }

""")

app, rt = fast_app(live=True, debug=True, hdrs=(custom_styles,))

# all future code goes in here


db = database('data/users.db')

users = db.t.users
comments = db.t.comments
likes = db.t.likes

# Create tables if they don't exist
if comments not in db.t:
    comments.create(dict(url=str, content=str, user_id=int), pk='id', date_created=datetime.now())

if users not in db.t:
    users.create(dict(email=str, password=str, id=int), pk='id')

if likes not in db.t:
    likes.create(dict(url=str, user_id=int, date_created=datetime), pk='id')

User = users.dataclass()
Comment = comments.dataclass()
Like = likes.dataclass()

def MyForm(btn_text, target):
    return Form(
        Input(id="email", type="email", placeholder="Email", required=True),
        Input(id="password", type="password", placeholder="Password", required=True),
        Button(btn_text, type="submit"),
        Span(id="error", style="color:red"),
        hx_post=target,
        hx_target="#error",
    )

@rt('/register', methods=['GET'])
def get():
    return Container(
        Article(
            H1("Register"),
            MyForm("Register", "/register"),
            Hr(),
            P("Already have an account? ", A("Login", href="/login")),
            cls="mw-480 mx-auto"
        )
    )

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password):
    return pwd_context.hash(password)

@rt('/register', methods=['POST'])
def post(email:str, password:str):

    try:
        users[email]
        return "User already exists"
    except NotFoundError:

        new_user = User(email=email, password=get_password_hash(password))

        users.insert(new_user)

        return HttpHeader('HX-Redirect', '/login')

@rt('/login', methods=['GET'])
def get():
    return Container(
        Article(
            H1("Login"),
            MyForm("Login", target="/login"),
            Hr(),
            P("Want to create an Account? ", A("Register", href="/register")),
            cls="mw-480 mx-auto"
        )
    )


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

@rt('/login', methods=['POST'])
def post(session, email:str, password:str):
    try:
        user = users[email]
    except NotFoundError:
        return "Email or password are incorrect"

    if not verify_password(password, user.password):
        return "Email or password are incorrect"

    session['auth'] = user.email

    return HttpHeader('HX-Redirect', '/dashboard')


def basic_auth(f):
    @wraps(f)
    def wrapper(session, *args, **kwargs):
        if "auth" not in session:
            # return Response('Not Authorized', status_code=401)
            return Container(Article(
                H1("Login"), 
                MyForm("Login", target="/login"), 
                Hr(), 
                P("Want to create an Account? ", A("Register", href="/register")), 
                cls="mw-480 mx-auto"))

        return f(session, *args, **kwargs)
    return wrapper

@rt('/dashboard')
@basic_auth
def get(session):    
    return Container(
        H1("Dashboard"),
        P(f"Add a comment {session['auth']}"),
        Form(
            Input(id="url", type="text", placeholder="URL", required=True),
            Input(id="content", type="text", placeholder="Comment", required=True),
            Button("Comment", hx_post="/comment"),
            hx_target="#comments",
            hx_trigger="submit",
            hx_swap="innerHTML",
            target_id="comments",
            hx_post="/comments",),
        Hr(),
        Button("Logout", hx_post="/logout")
    )


@rt('/logout')
def post(session):
    del session['auth']
    return HttpHeader('HX-Redirect', '/login')


@rt('/comment')
def post(session, url:str, content:str):
    if "auth" not in session:
        return "Not authorized"

    user = users[session['auth']]

    # Here you would save the comment to the database
    # For example:
    date = datetime.now()
    comments.insert(Comment(url=url, content=content, user_id=user.id, date_created=date))

    return "Comment saved"

@rt('/like/{url}', methods=['POST'])
@basic_auth
def post(session, url:str):
    if "auth" not in session:
        return "Not authorized"

    user = users[session['auth']]

    # Here you would save the like to the database
    # For example:
    date = datetime.now()
    likes.insert(Like(url=url, user_id=user.id, date_created=date))
    likes.commit()
    return "Like saved"

@rt('/likes/{url}', methods=['GET'])
def get(session, url:str):
 
    # Here you would retrieve the likes from the database
    # For example:
    # user_likes = likes.where(likes.url == url).all()

    qry = "select * from likes where url = ':url'"
    qry = qry.replace(':url', url)

    print(qry)

    result = db.q(qry)

    user_likes = len(result)

    print(user_likes)
    # user_likes = likes.url == url.all()

    return Container(
        H1("Likes"),
        P(f"Likes: {user_likes}", name="likes")
    )

@rt('/get_comments')
def get(session, url:str):

    # Here you would retrieve the comments from the database
    # For example:
    # user_comments = comments.where(comments.url == url).all()

    # user_comments = session.exec(select(comments).where(comments.url == url)).all()
    
    qry = "select * from comments where url = ':url'"
    qry = qry.replace(':url', url)

    print(qry)

    user_comments = db.q(qry)

    print(user_comments)
    # user_comments = comments.url == url.all()

    for comment in user_comments:
        print(comment['content'])
        # comment.user = users[comment.user_id]

    return Container(
        H1("Comments"),
        *[P(comment['content']) for comment in user_comments]
    )

@rt('/test')
@basic_auth
def test(session):

    qry = "select * from likes where url = '/test'"
    result = db.q(qry)
    like_count = len(result)
    print(f"like_count {like_count}")

    return Container(
        H1("Test"),
        P(f"Hello {session['auth']}"),
        P(f"likes {like_count}", name="likes"),
        Button("Like", hx_post="/like/test", hx_target="#likes", hx_swap_oob="innerHTML"),
        
    )


serve()
