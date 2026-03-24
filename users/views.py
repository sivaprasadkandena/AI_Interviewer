import json
import re
import random
from urllib.parse import urlencode

from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib import messages
from django.views.decorators.cache import never_cache
from django.core.mail import send_mail

from authlib.integrations.django_client import OAuth

from .forms import CandidateForm, AnswerForm, ProfileCompletionForm
from .models import Candidate, InterviewResponse, RegisteredUser

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage


llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=settings.GOOGLE_API_KEY,
    temperature=0.7,
)

oauth = OAuth()
oauth.register(
    name='keycloak',
    client_id=settings.AUTHLIB_OAUTH_CLIENTS['keycloak']['client_id'],
    client_secret=settings.AUTHLIB_OAUTH_CLIENTS['keycloak']['client_secret'],
    server_metadata_url=settings.AUTHLIB_OAUTH_CLIENTS['keycloak']['server_metadata_url'],
    client_kwargs=settings.AUTHLIB_OAUTH_CLIENTS['keycloak']['client_kwargs'],
)


def generate_question(messages):
    langchain_messages = [SystemMessage(content="You are an AI interviewer.")]
    for msg in messages:
        langchain_messages.append(HumanMessage(content=msg["content"]))
    response = llm.invoke(langchain_messages)
    return response.content.strip()


def evaluate_answer(question, answer):
    prompt = (
        f"Evaluate the following candidate answer to the interview question.\n\n"
        f"Question: {question}\n"
        f"Answer: {answer}\n\n"
        f'Respond in JSON format like: {{"score": <0-5>, "qualified": "yes" or "no"}}\n'
        f"Only respond with valid JSON. No explanations."
    )

    result = llm.invoke([HumanMessage(content=prompt)])
    content = result.content.strip()

    try:
        parsed = json.loads(content)
        return {
            "score": int(parsed.get("score", 0)),
            "qualified": parsed.get("qualified", "no")
        }
    except Exception:
        try:
            match = re.search(r'{.*}', content)
            if match:
                parsed = json.loads(match.group())
                return {
                    "score": int(parsed.get("score", 0)),
                    "qualified": parsed.get("qualified", "no")
                }
        except Exception:
            pass

    return {"score": 0, "qualified": "no"}


# ---------------------------
# SSO AUTH VIEWS
# ---------------------------

def index(request):
    if 'user' in request.session:
        return redirect('home')
    return render(request, 'index.html')


@never_cache
def register_view(request):
    messages.info(request, "Registration is handled through Keycloak.")
    return redirect('user_login')


@never_cache
def user_login(request):
    if 'user' in request.session:
        return redirect('home')

    redirect_uri = request.build_absolute_uri('/auth/callback/')
    return oauth.keycloak.authorize_redirect(request, redirect_uri)


@never_cache
def callback_view(request):
    token = oauth.keycloak.authorize_access_token(request)
    userinfo = token.get('userinfo')

    if not userinfo:
        userinfo = oauth.keycloak.userinfo(token=token)

    sub = userinfo.get('sub')
    username = userinfo.get('preferred_username')
    email = userinfo.get('email')
    name = userinfo.get('name')

    request.session['user'] = {
        'sub': sub,
        'username': username,
        'email': email,
        'name': name,
    }
    request.session['id_token'] = token.get('id_token')

    profile, created = RegisteredUser.objects.get_or_create(
        keycloak_sub=sub,
        defaults={
            'username': username,
            'email': email,
            'name': name,
            'is_active': True,
        }
    )

    changed = False
    if not profile.username and username:
        profile.username = username
        changed = True
    if not profile.email and email:
        profile.email = email
        changed = True
    if not profile.name and name:
        profile.name = name
        changed = True
    if changed:
        profile.save()

    if not profile.name or not profile.mobile or not profile.image:
        return redirect('complete_profile')

    messages.success(request, f"Welcome, {username}!")
    return redirect('home')


@never_cache
def user_logout(request):
    id_token = request.session.get('id_token')
    request.session.pop('user', None)
    request.session.pop('id_token', None)
    request.session.flush()

    redirect_uri = request.build_absolute_uri('/auth/login/')
    params = {
        "post_logout_redirect_uri": redirect_uri,
        "id_token_hint": id_token,
    }

    logout_url = (
        "http://localhost:8080/realms/sso-demo/protocol/openid-connect/logout?"
        + urlencode(params)
    )
    return redirect(logout_url)


@never_cache
def home(request):
    if 'user' not in request.session:
        return redirect('user_login')

    profile = RegisteredUser.objects.filter(
        keycloak_sub=request.session['user'].get('sub')
    ).first()

    if not profile or not profile.name or not profile.mobile or not profile.image:
        return redirect('complete_profile')

    return render(request, 'home.html', {
        'user': request.session.get('user'),
        'profile': profile,
    })


@never_cache
def complete_profile(request):
    if 'user' not in request.session:
        return redirect('user_login')

    sso_user = request.session['user']
    sub = sso_user.get('sub')

    profile, created = RegisteredUser.objects.get_or_create(
        keycloak_sub=sub,
        defaults={
            'username': sso_user.get('username'),
            'email': sso_user.get('email'),
            'name': sso_user.get('name'),
            'is_active': True,
        }
    )

    if request.method == 'POST':
        form = ProfileCompletionForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile completed successfully!")
            return redirect('home')
    else:
        form = ProfileCompletionForm(instance=profile)

    return render(request, 'users/complete_profile.html', {
        'form': form,
        'user': sso_user,
    })


@never_cache
def user_homepage(request):
    if 'user' not in request.session:
        return redirect('user_login')

    profile = RegisteredUser.objects.filter(
        keycloak_sub=request.session['user'].get('sub')
    ).first()

    return render(request, 'users/user_homepage.html', {
        'user': request.session.get('user'),
        'profile': profile,
    })


# ---------------------------
# KEEP INTERVIEW FEATURES
# ---------------------------

def start_interview(request):
    if 'user' not in request.session:
        return redirect('user_login')

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

            request.session['messages'] = [{
                "content": f"""
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
            request.session['messages'].append({"content": first_question})

            return render(request, 'users/question.html', {
                'question': first_question,
                'form': AnswerForm()
            })
    else:
        form = CandidateForm()

    return render(request, 'users/start.html', {'form': form})


def answer_question(request):
    if 'user' not in request.session:
        return redirect('user_login')

    candidate_id = request.session.get('candidate_id')
    question_count = request.session.get('question_count', 1)
    messages_list = request.session.get('messages', [])

    candidate = Candidate.objects.get(id=candidate_id)

    if request.method == 'POST':
        form = AnswerForm(request.POST)
        if form.is_valid():
            answer = form.cleaned_data['answer']
            last_question = messages_list[-1]['content']

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

            messages_list.append({"content": answer})
            messages_list.append({
                "content": (
                    "Ask ONE more very simple Python interview question.\n"
                    "Rules:\n"
                    "- Beginner level\n"
                    "- 1 or 2 lines only\n"
                    "- No explanation\n"
                    "- Just the question\n"
                )
            })

            next_question = generate_question(messages_list)
            messages_list.append({"content": next_question})
            request.session['messages'] = messages_list

            return render(request, 'users/question.html', {
                'question': next_question,
                'form': AnswerForm()
            })

    return render(request, 'users/question.html', {
        'question': messages_list[-1]['content'],
        'form': AnswerForm()
    })


def interview_results(request, candidate_id):
    if 'user' not in request.session:
        return redirect('user_login')

    candidate = Candidate.objects.get(id=candidate_id)
    responses = InterviewResponse.objects.filter(candidate=candidate)
    total_score = sum(r.score for r in responses if r.score is not None)
    avg_score = total_score / len(responses) if responses else 0
    status = "Qualified" if avg_score >= 3 else "Disqualified"

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
    if 'user' not in request.session:
        return redirect('user_login')

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


# ---------------------------
# OPTIONAL: KEEP ADMIN PAGES
# ---------------------------

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