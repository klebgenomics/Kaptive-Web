def captcha_field(request=request):
    from gluon.tools import Recaptcha2
    w = lambda x, y: Recaptcha2(request,
                                '6LckfBMUAAAAACrjs24Fp--R5N5k9j3VCxA2LYNN',
                                '6LckfBMUAAAAAAQ17RsRcik73rSGlMIR1nAnUPGz',
                                error_message='Invalid, please try again.')
    return Field('captcha', 'string', label=T('Verify'), widget=w, default='ok')
