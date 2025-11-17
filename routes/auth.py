"""
Authentication routes (login, register, logout).
Unified routes supporting both web UI and API.
"""
from flask import Blueprint, render_template, redirect, url_for, request, make_response, current_app
from flask_jwt_extended import set_access_cookies, unset_jwt_cookies
from functools import wraps
from urllib.parse import urlparse

from models import db, User
from forms import (
    LoginForm, RegistrationForm, ChangePasswordForm,
    RequestPasswordResetForm, ResetPasswordForm
)
from services.auth_service import AuthService
from utils.responses import wants_json, success_response, error_response, unified_response
from utils.auth import login_required, get_current_user

bp = Blueprint('auth', __name__, url_prefix='/auth')


def rate_limit(limit_string):
    """No-op rate limiting decorator (limiter removed).

    Keeps decorator in place so routes using @rate_limit continue to work,
    but does not perform any limiting.
    """
    def decorator(f):
        return f
    return decorator


@bp.route('/register', methods=['GET', 'POST'])
@rate_limit("5 per hour")
def register():
    """User registration - unified for web and API."""
    current_user = get_current_user()
    if current_user:
        if wants_json():
            return error_response('Already authenticated', status_code=400)
        return redirect(url_for('main.index'))
    
    if request.method == 'POST' and wants_json():
        data = request.get_json()
        if not data or not all(k in data for k in ['username', 'email', 'password']):
            return error_response('Username, email, and password are required', status_code=400)
        
        result = AuthService.register_user(
            username=data['username'],
            email=data['email'],
            password=data['password']
        )
        
        if not result['success']:
            return error_response(result['message'], status_code=400)
        
        return unified_response({
            'success': True,
            'message': result['message'],
            'access_token': result['token'],
            'user': AuthService.user_to_dict(result['user'])
        }, status_code=201)
    
    form = RegistrationForm()
    if form.validate_on_submit():
        result = AuthService.register_user(
            username=form.username.data,
            email=form.email.data,
            password=form.password.data
        )
        
        if not result['success']:
            return error_response(
                result['message'],
                template_name='auth/register.html',
                form=form,
                title='Register'
            )
        
        response = make_response(success_response(
            result['message'],
            redirect_url=url_for('main.index')
        ))
        set_access_cookies(response, result['token'])
        return response
    
    return render_template('auth/register.html', title='Register', form=form)


@bp.route('/login', methods=['GET', 'POST'])
@rate_limit("10 per hour")
def login():
    """User login - unified for web and API."""
    current_user = get_current_user()
    if current_user:
        if wants_json():
            return error_response('Already authenticated', status_code=400)
        return redirect(url_for('main.index'))
    
    if request.method == 'POST' and wants_json():
        data = request.get_json()
        if not data or not all(k in data for k in ['email', 'password']):
            return error_response('Email and password are required', status_code=400)
        
        result = AuthService.login_user(
            email=data['email'],
            password=data['password']
        )
        
        if not result['success']:
            return error_response(result['message'], status_code=401)
        
        return unified_response({
            'success': True,
            'message': result['message'],
            'access_token': result['token'],
            'user': AuthService.user_to_dict(result['user'])
        })
    
    form = LoginForm()
    if form.validate_on_submit():
        result = AuthService.login_user(
            email=form.email.data,
            password=form.password.data
        )
        
        if not result['success']:
            return error_response(
                result['message'],
                template_name='auth/login.html',
                form=form,
                title='Log In'
            )
        
        next_page = request.args.get('next')
        if not next_page or urlparse(next_page).netloc != '':
            next_page = url_for('main.index')
        
        response = make_response(success_response(
            result['message'],
            redirect_url=next_page
        ))
        set_access_cookies(response, result['token'])
        return response
    
    return render_template('auth/login.html', title='Log In', form=form)


@bp.route('/logout', methods=['GET', 'POST'])
def logout():
    """User logout - unified for web and API."""
    if wants_json():
        response = make_response(unified_response({
            'success': True,
            'message': 'You have been logged out.'
        }))
    else:
        response = make_response(success_response(
            'You have been logged out.',
            redirect_url=url_for('main.index')
        ))
    
    unset_jwt_cookies(response)
    return response


@bp.route('/delete-account', methods=['POST'])
@login_required()
def delete_account(current_user):
    """Delete user account and all associated data."""
    result = AuthService.delete_account(current_user)
    
    if wants_json():
        response = make_response(unified_response({
            'success': True,
            'message': result['message']
        }))
    else:
        response = make_response(success_response(
            result['message'],
            redirect_url=url_for('main.index')
        ))
    
    unset_jwt_cookies(response)
    return response


@bp.route('/change-password', methods=['GET', 'POST'])
@login_required()
def change_password(current_user):
    """Change user password."""
    if request.method == 'POST' and wants_json():
        data = request.get_json()
        if not data or not all(k in data for k in ['current_password', 'new_password']):
            return error_response('Current password and new password are required', status_code=400)
        
        result = AuthService.change_password(
            user=current_user,
            current_password=data['current_password'],
            new_password=data['new_password']
        )
        
        if not result['success']:
            return error_response(result['message'], status_code=400)
        
        return unified_response({
            'success': True,
            'message': result['message']
        })
    
    form = ChangePasswordForm()
    if form.validate_on_submit():
        result = AuthService.change_password(
            user=current_user,
            current_password=form.current_password.data,
            new_password=form.new_password.data
        )
        
        if not result['success']:
            return error_response(
                result['message'],
                template_name='auth/change_password.html',
                form=form,
                title='Change Password'
            )
        
        return success_response(
            result['message'],
            redirect_url=url_for('movies.profile')
        )
    
    return render_template('auth/change_password.html', title='Change Password', form=form)


@bp.route('/reset-password-request', methods=['GET', 'POST'])
def reset_password_request():
    """Request password reset."""
    current_user = get_current_user()
    if current_user:
        if wants_json():
            return error_response('Already authenticated', status_code=400)
        return redirect(url_for('main.index'))
    
    if request.method == 'POST' and wants_json():
        data = request.get_json()
        if not data or 'email' not in data:
            return error_response('Email is required', status_code=400)
        
        result = AuthService.request_password_reset(email=data['email'])
        response_data = {
            'success': True,
            'message': result['message']
        }
        if result.get('token') and not result.get('email_sent'):
            response_data['reset_token'] = result['token']
        
        return unified_response(response_data)
    
    form = RequestPasswordResetForm()
    if form.validate_on_submit():
        result = AuthService.request_password_reset(email=form.email.data)
        return success_response(
            result['message'],
            redirect_url=url_for('auth.login')
        )
    
    return render_template('auth/reset_password_request.html', title='Reset Password', form=form)


@bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Reset password with token."""
    current_user = get_current_user()
    if current_user:
        if wants_json():
            return error_response('Already authenticated', status_code=400)
        return redirect(url_for('main.index'))
    
    user = User.verify_reset_token(token)
    if not user:
        return error_response(
            'Invalid or expired password reset link.',
            status_code=400,
            redirect_url=url_for('auth.reset_password_request')
        )
    
    if request.method == 'POST' and wants_json():
        data = request.get_json()
        if not data or 'password' not in data:
            return error_response('Password is required', status_code=400)
        
        result = AuthService.reset_password(token=token, new_password=data['password'])
        if not result['success']:
            return error_response(result['message'], status_code=400)
        
        return unified_response({
            'success': True,
            'message': result['message']
        })
    
    form = ResetPasswordForm()
    if form.validate_on_submit():
        result = AuthService.reset_password(token=token, new_password=form.password.data)
        if not result['success']:
            return error_response(
                result['message'],
                template_name='auth/reset_password.html',
                form=form,
                title='Reset Password'
            )
        
        return success_response(
            result['message'],
            redirect_url=url_for('auth.login')
        )
    
    return render_template('auth/reset_password.html', title='Reset Password', form=form)
