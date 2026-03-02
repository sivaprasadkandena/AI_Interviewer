

import json
from django.conf import settings
from django.shortcuts import render, redirect
from .forms import CandidateForm, AnswerForm
from .models import Candidate, InterviewResponse

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=settings.GOOGLE_API_KEY,
    temperature=0.7,
)

def generate_question(messages):
    langchain_messages = [SystemMessage(content="You are an AI interviewer.")]
    for msg in messages:
        langchain_messages.append(HumanMessage(content=msg["content"]))
    response = llm.invoke(langchain_messages)
    return response.content.strip()


import re
import json

def evaluate_answer(question, answer):
    prompt = (
        f"Evaluate the following candidate answer to the interview question.\n\n"
        f"Question: {question}\n"
        f"Answer: {answer}\n\n"
        f"Respond in JSON format like:\n"
        f'{{"score": <0-5>, "qualified": "yes" or "no"}}\n'
        f"Only respond with valid JSON. No explanations."
    )

    result = llm.invoke([HumanMessage(content=prompt)])
    content = result.content.strip()

    # Try JSON parse first
    try:
        parsed = json.loads(content)
        score = int(parsed.get("score", 0))
        qualified = parsed.get("qualified", "no")
        return {"score": score, "qualified": qualified}
    except Exception:
        # Try to extract JSON with regex
        try:
            match = re.search(r'{.*}', content)
            if match:
                extracted_json = match.group()
                parsed = json.loads(extracted_json)
                score = int(parsed.get("score", 0))
                qualified = parsed.get("qualified", "no")
                return {"score": score, "qualified": qualified}
        except:
            pass

    # Default fallback if all parsing fails
    return {"score": 0, "qualified": "no"}


def start_interview(request):
    if request.method == 'POST':
        form = CandidateForm(request.POST)

        if form.is_valid():
            candidate = Candidate.objects.create(
                name=form.cleaned_data['name'],
                email=form.cleaned_data['email'],
                job_description=form.cleaned_data['job_description']
            )

            request.session['candidate_id'] = candidate.id

            job_desc = form.cleaned_data['job_description']

            # UPDATED PROMPT
            request.session['messages'] = [{
                "content":f"""
                    You are an AI technical interviewer.

                    The candidate applied for a role with the following job description:

                    {job_desc}

                    Generate ONE beginner-level technical interview question related to the required skills.

                    Rules:
                    - 1 or 2 lines
                    - No explanation
                    - No examples
                    - No headings
                    - Only the question
                    """
            }]

            request.session['question_count'] = 1

            first_question = generate_question(request.session['messages'])

            request.session['messages'].append({
                "content": first_question
            })

            return render(request, 'users/question.html', {
                'question': first_question,
                'form': AnswerForm()
            })

    else:
        form = CandidateForm()

    return render(request, 'users/start.html', {'form': form})

def answer_question(request):
    candidate_id = request.session.get('candidate_id')
    question_count = request.session.get('question_count', 1)
    messages = request.session.get('messages', [])

    candidate = Candidate.objects.get(id=candidate_id)

    if request.method == 'POST':
        form = AnswerForm(request.POST)
        if form.is_valid():
            answer = form.cleaned_data['answer']
            last_question = messages[-1]['content']

            evaluation = evaluate_answer(last_question, answer)

            InterviewResponse.objects.create(
                candidate=candidate,
                question=last_question,
                answer=answer,
                score=evaluation.get("score", 0)
            )

            if question_count >= 4:
                return redirect('interview_results', candidate_id=candidate.id)

            question_count += 1
            request.session['question_count'] = question_count

            messages.append({"content": answer})

            # 🔴 FIXED PROMPT
            messages.append({
                "content": (
                    "Ask ONE more very simple Python interview question.\n"
                    "Rules:\n"
                    "- Beginner level\n"
                    "- 1 or 2 lines only\n"
                    "- No explanation\n"
                    "- Just the question\n"
                )
            })

            next_question = generate_question(messages)
            messages.append({"content": next_question})
            request.session['messages'] = messages

            return render(request, 'users/question.html', {
                'question': next_question,
                'form': AnswerForm()
            })

    return render(request, 'users/question.html', {
        'question': messages[-1]['content'],
        'form': AnswerForm()
    })


from django.core.mail import send_mail
def interview_results(request, candidate_id):
    candidate = Candidate.objects.get(id=candidate_id)
    responses = InterviewResponse.objects.filter(candidate=candidate)
    total_score = sum(r.score for r in responses if r.score is not None)
    avg_score = total_score / len(responses) if responses else 0
    status = "Qualified" if avg_score >= 3 else "Disqualified"

    # Email subject and body based on status
    if status == "Qualified":
        subject = "🎉 Congratulations! You are Qualified"
        message = (
            f"Dear {candidate.name},\n\n"
            f"Congratulations on successfully completing your interview for the position of {candidate.job_description}.\n"
            f"Your average score is {avg_score:.2f}. We are happy to inform you that you are qualified & offer letter should be released soon.\n\n"
            f"Regards,\nAI Interview Team"
        )
    else:
        subject = "📩 Interview Result - Not Qualified"
        message = (
            f"Dear {candidate.name},\n\n"
            f"Thank you for attending the interview for the position of {candidate.job_description}.\n"
            f"Your average score is {avg_score:.2f}. Unfortunately, you have not qualified this time.\n\n"
            f"We encourage you to keep learning and try again.\n\n"
            f"Best wishes,\nAI Interview Team"
        )

    # Send email
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [candidate.email],
        fail_silently=False,
    )

    return render(request, 'users/results.html', {
        'candidate': candidate,
        'responses': responses,
        'avg_score': avg_score,
        'qualification_status': status
    })
def all_results(request):
    candidates = Candidate.objects.all().order_by('-id')
    results = []
    for c in candidates:
        responses = InterviewResponse.objects.filter(candidate=c)
        total_score = sum(r.score for r in responses if r.score is not None)
        avg_score = total_score / len(responses) if responses else 0
        status = "Qualified" if avg_score >= 3 else "Disqualified"
        results.append({
            'candidate': c,
            'avg_score': avg_score,
            'status': status,
        })
    return render(request, 'users/all_results.html', {'results': results})

###  code for home and logins
def index(request):
    return render(request, 'index.html')



from django.shortcuts import render, redirect
from .models import RegisteredUser
from django.core.files.storage import FileSystemStorage

def register_view(request):
    msg = ''
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        mobile = request.POST.get('mobile')
        password = request.POST.get('password')
        image = request.FILES.get('image')

        # Basic validation
        if not (name and email and mobile and password and image):
            msg = "All fields are required."
        else:
            # Save image manually
            fs = FileSystemStorage()
            filename = fs.save(image.name, image)
            img_url = fs.url(filename)

            # Save user with is_active=False
            RegisteredUser.objects.create(
                name=name,
                email=email,
                mobile=mobile,
                password=password,
                image=filename,
                is_active=False
            )
            msg = "Registered successfully! Wait for admin approval."

    return render(request, 'register.html', {'msg': msg})

from django.utils import timezone

from django.utils import timezone
import pytz

def user_login(request):
    msg = ''
    if request.method == 'POST':
        name = request.POST.get('name')
        password = request.POST.get('password')

        try:
            user = RegisteredUser.objects.get(name=name, password=password)
            if user.is_active:
                # Convert current time to IST
                ist = pytz.timezone('Asia/Kolkata')
                local_time = timezone.now().astimezone(ist)

                # Save user info in session
                request.session['user_id'] = user.id
                request.session['user_name'] = user.name
                request.session['user_image'] = user.image.url  # image URL
                request.session['login_time'] = local_time.strftime('%I:%M:%S %p')

                return redirect('user_homepage')
            else:
                msg = "Your account is not activated yet."
        except RegisteredUser.DoesNotExist:
            msg = "Invalid credentials."

    return render(request, 'user_login.html', {'msg': msg})

def admin_login(request):
    msg = ''
    if request.method == 'POST':
        name = request.POST.get('name')
        password = request.POST.get('password')

        if name == 'admin' and password == 'admin':
            return redirect('admin_home')
        else:
            msg = "Invalid admin credentials."

    return render(request, 'admin_login.html', {'msg': msg})

def admin_home(request):
    return render(request, 'admin_home.html')
    
def admin_dashboard(request):
    users = RegisteredUser.objects.all()
    return render(request, 'admin_dashboard.html', {'users': users})

def activate_user(request, user_id):
    user = RegisteredUser.objects.get(id=user_id)
    user.is_active = True
    user.save()
    return redirect('admin_dashboard')

def deactivate_user(request, user_id):
    user = RegisteredUser.objects.get(id=user_id)
    user.is_active = False
    user.save()
    return redirect('admin_dashboard')

def delete_user(request, user_id):
    user = RegisteredUser.objects.get(id=user_id)
    user.delete()
    return redirect('admin_dashboard')



def home(request):
    return render(request, 'home.html')

def user_homepage(request):
    if 'user_id' not in request.session:
        # User not logged in, redirect to login page
        return redirect('user_login')

    user_name = request.session.get('user_name')
    user_image = request.session.get('user_image')
    login_time = request.session.get('login_time')

    context = {
        'user_name': user_name,
        'user_image': user_image,
        'login_time': login_time,
    }
    return render(request, 'users/user_homepage.html', context)

def user_logout(request):
    request.session.flush()  # Clears all session data
    return redirect('user_login')



import random
from django.shortcuts import render, redirect
from django.core.mail import send_mail
from django.contrib import messages
from .models import RegisteredUser

otp_storage = {}  # Temporary dictionary to store OTPs

def send_otp(email):
    otp = random.randint(100000, 999999)  # Generate a 6-digit OTP
    otp_storage[email] = otp

    subject = "Password Reset OTP"
    message = f"Your OTP for password reset is: {otp}"
    from_email = "saikumardatapoint1@gmail.com"  # Change this to your email
    send_mail(subject, message, from_email, [email])

    return otp

def forgot_password(request):
    if request.method == "POST":
        email = request.POST.get("email")

        if RegisteredUser.objects.filter(email=email).exists():
            send_otp(email)
            request.session["reset_email"] = email  # Store email in session
            return redirect("verify_otp")
        else:
            messages.error(request, "Email not registered!")

    return render(request, "forgot_password.html")

def verify_otp(request):
    if request.method == "POST":
        otp_entered = request.POST.get("otp")
        email = request.session.get("reset_email")

        if otp_storage.get(email) and str(otp_storage[email]) == otp_entered:
            return redirect("reset_password")
        else:
            messages.error(request, "Invalid OTP!")

    return render(request, "verify_otp.html")

def reset_password(request):
    if request.method == "POST":
        new_password = request.POST.get("new_password")
        email = request.session.get("reset_email")

        if RegisteredUser.objects.filter(email=email).exists():
            user = RegisteredUser.objects.get(email=email)
            user.password = new_password  # Updating password
            user.save()
            messages.success(request, "Password reset successful! Please log in.")
            return redirect("user_login")

    return render(request, "reset_password.html")

