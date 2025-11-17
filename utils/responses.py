"""
Response utilities for unified routes.
Handles content negotiation between JSON (API) and HTML (web UI).
"""
from flask import request, jsonify, render_template, make_response


def wants_json():
    """
    Check if client wants JSON response.
    
    Returns True if:
    - Content-Type is application/json
    - Accept header prefers JSON over HTML
    - X-Requested-With is XMLHttpRequest (AJAX)
    """
    # Check if request has JSON content type
    if request.is_json:
        return True
    
    # Check if client explicitly accepts JSON
    best = request.accept_mimetypes.best_match(['application/json', 'text/html'])
    if best == 'application/json':
        return True
    
    # Check for AJAX requests
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return True
    
    return False


def unified_response(data, template_name=None, status_code=200, **template_kwargs):
    """
    Return JSON for API clients or HTML for web browsers.
    
    Args:
        data: Dictionary with response data
        template_name: Template to render for HTML responses
        status_code: HTTP status code
        **template_kwargs: Additional kwargs for template rendering
    
    Returns:
        JSON response or rendered HTML template
    """
    if wants_json():
        return jsonify(data), status_code
    
    if template_name:
        # Merge data into template_kwargs
        template_kwargs.update(data)
        return render_template(template_name, **template_kwargs), status_code
    
    # Fallback: return JSON if no template provided
    return jsonify(data), status_code


def success_response(message, data=None, template_name=None, redirect_url=None, **template_kwargs):
    """
    Unified success response.
    
    For JSON: Returns {'success': True, 'message': '...', ...}
    For HTML: Shows flash message and renders template or redirects
    """
    response_data = {
        'success': True,
        'message': message
    }
    
    if data:
        response_data.update(data)
    
    if wants_json():
        return jsonify(response_data), 200
    
    # HTML response
    from flask import flash, redirect, url_for
    
    flash(message, 'success')
    
    if redirect_url:
        return redirect(redirect_url)
    
    if template_name:
        return render_template(template_name, **template_kwargs)
    
    # Default: redirect to home
    return redirect(url_for('main.index'))


def error_response(message, status_code=400, template_name=None, redirect_url=None, **template_kwargs):
    """
    Unified error response.
    
    For JSON: Returns {'success': False, 'message': '...'}
    For HTML: Shows flash message and renders template or redirects
    """
    response_data = {
        'success': False,
        'message': message
    }
    
    if wants_json():
        return jsonify(response_data), status_code
    
    # HTML response
    from flask import flash, redirect, url_for
    
    # Map status codes to flash categories
    category_map = {
        400: 'warning',
        401: 'danger',
        403: 'danger',
        404: 'warning',
        500: 'danger'
    }
    category = category_map.get(status_code, 'warning')
    
    flash(message, category)
    
    if redirect_url:
        return redirect(redirect_url)
    
    if template_name:
        return render_template(template_name, **template_kwargs), status_code
    
    # Default: redirect to home
    return redirect(url_for('main.index'))
