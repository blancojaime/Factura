"""Envio multicanal de Fichas de Cotizacion: correo (SMTP opcional), enlace de WhatsApp e impresion."""
import smtplib
import urllib.parse
from email.message import EmailMessage

from ..config import get_settings


def enviar_correo(destino: str, asunto: str, cuerpo: str, adjunto: bytes | None = None,
                  nombre_adjunto: str = "ficha.pdf") -> str:
    """Devuelve ENVIADO | NO_CONFIGURADO | SIN_CORREO | ERROR:<detalle>."""
    s = get_settings()
    if not destino:
        return "SIN_CORREO"
    if not s.smtp_host:
        return "NO_CONFIGURADO"
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = s.smtp_from, destino, asunto
    msg.set_content(cuerpo)
    if adjunto:
        msg.add_attachment(adjunto, maintype="application", subtype="pdf", filename=nombre_adjunto)
    try:
        with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=15) as smtp:
            smtp.starttls()
            if s.smtp_user:
                smtp.login(s.smtp_user, s.smtp_password)
            smtp.send_message(msg)
        return "ENVIADO"
    except Exception as exc:  # noqa: BLE001 - se informa al usuario sin abortar el tramite
        return f"ERROR:{type(exc).__name__}"


def enlace_whatsapp(telefono: str, texto: str) -> str:
    digitos = "".join(ch for ch in (telefono or "") if ch.isdigit())
    if digitos and len(digitos) == 8:  # numero local boliviano -> prefijo pais
        digitos = "591" + digitos
    if not digitos:
        return ""
    return f"https://wa.me/{digitos}?text={urllib.parse.quote(texto)}"
