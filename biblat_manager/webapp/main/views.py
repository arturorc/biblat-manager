# -*- coding: utf-8 -*-
import socket
from flask import (request,
                   session,
                   current_app,
                   redirect,
                   url_for,
                   abort,
                   render_template,
                   flash)
from flask_babelex import gettext as _, lazy_gettext as __
from flask_breadcrumbs import register_breadcrumb

from . import main
from biblat_manager.webapp import babel
from biblat_manager.webapp import babel, controllers
from biblat_manager.webapp.forms import (
    RegistrationForm
)
from biblat_manager.webapp.models import User
from biblat_manager.webapp.utils import get_timed_serializer


@main.route('/', methods=['GET', 'POST'])
@register_breadcrumb(main, '.', __('Inicio'))
def index():
    data = {
        'html_title': 'Biblat Manager - Index'
    }
    flash('You successfully read this important success message.', 'success')
    flash('You successfully read this important error message.', 'error')
    flash('You successfully read this important warning message.', 'warning')
    flash('You successfully read this important info message.', 'info')
    return render_template('main/index.html', **data)


@main.route('/revistas', methods=['GET', 'POST'])
@register_breadcrumb(main, '.revistas', __('Revistas'))
def revistas():
    data = {
        'html_title': 'Biblat Manager - Revistas'
    }
    return render_template('main/index.html', **data)


# i18n
@babel.localeselector
def get_locale():
    langs = current_app.config.get('LANGUAGES')
    lang_from_headers = request.accept_languages.best_match(list(langs.keys()))

    if 'lang' not in list(session.keys()):
        session['lang'] = lang_from_headers

    if not lang_from_headers and not session['lang']:
        # Si no se puede detectar el idioma se asigna el predeterminado
        session['lang'] = current_app.config.get('BABEL_DEFAULT_LOCALE')

    return session['lang']


@main.route('/set_locale/<string:lang_code>/')
def set_locale(lang_code):
    langs = current_app.config.get('LANGUAGES')

    if lang_code not in list(langs.keys()):
        abort(400, _(u'Código de idioma inválido'))

    # Guardar lang_code en sesión
    session['lang'] = lang_code

    if request.referrer is None:
        return redirect(url_for('main.index'))
    return redirect(request.referrer)


@main.route('/menutoggle/')
def set_menutoggle():
    session['menutoggle'] = 'open' \
        if session.get('menutoggle', '') == '' else ''
    return session['menutoggle']


# USER


@main.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if request.method == 'POST' and form.validate():
        existing_user = User.objects(email=form.email.data).first()
        if existing_user is None:
            user_data = {
                'username': form.username.data,
                'email': form.email.data,
                'password': form.password.data
            }
            user = User(**user_data).save()
            if user.id:
                try:
                    was_sent, error_msg = user.send_confirmation_email()
                except (ValueError, socket.error) as e:
                    was_sent = False
                    error_msg = e.message
                # Enviamos el email de confirmación a el usuario.
                if was_sent:
                    flash(_('Se envío un correo de confirmación a: %(email)s',
                            email=user.email), 'info')
                else:
                    flash(_('Ocurrió un error en el envío del correo de '
                            'confirmación  a: %(email)s %(error_msg)s',
                            email=user.email, error_msg=error_msg),
                          'error')
        else:
            flash(_('El correo electrónico ya esta registrado'), 'error')
    return render_template('forms/register.html', form=form)


@main.route('/confirm/<token>')
def confirm_email(token):
    try:
        ts = get_timed_serializer()
        email = ts.loads(token,
                         salt=current_app.config.get('TOKEN_EMAIL_SALT'),
                         max_age=current_app.config.get('TOKEN_MAX_AGE'))
    except Exception:  # posibles exepciones: https://pythonhosted.org/itsdangerous/#exceptions
        abort(404)

    user = controllers.get_user_by_email(email=email)
    if not user:
        abort(404, _('Usuario no encontrado'))

    controllers.set_user_email_confirmed(user)
    flash(_('Email: %(email)s confirmado com éxito!', email=user.email), 'success')
    return redirect(url_for('.index'))

