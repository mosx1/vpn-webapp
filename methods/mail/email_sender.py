"""Отправка email через Яндекс Почту."""

from __future__ import annotations

import smtplib
from email.message import EmailMessage
from email.utils import formataddr
from ssl import create_default_context

from config_loader import read_config


class YandexEmailSender:
    """SMTP-отправитель писем через аккаунт Яндекс Почты."""

    CONFIG_SECTION = "YandexMail"

    def __init__(self) -> None:
        config = read_config()
        if not config.has_section(self.CONFIG_SECTION):
            raise RuntimeError(
                "В config.ini нет секции [YandexMail]. "
                "Добавьте параметры SMTP для Яндекс Почты."
            )

        section = config[self.CONFIG_SECTION]
        self.smtp_host = section.get("smtp_host", "smtp.yandex.ru").strip()
        self.smtp_port = section.getint("smtp_port", fallback=465)
        self.login = section.get("login", "").strip()
        self.password = section.get("password", "").strip()
        self.from_email = section.get("from_email", self.login).strip()
        self.from_name = section.get("from_name", "").strip()
        self.use_ssl = section.getboolean("use_ssl", fallback=True)
        self.use_tls = section.getboolean("use_tls", fallback=False)

        self._validate_config()

    def _validate_config(self) -> None:
        if not self.login:
            raise RuntimeError("В секции [YandexMail] не заполнен параметр login.")
        if not self.password:
            raise RuntimeError("В секции [YandexMail] не заполнен параметр password.")
        if not self.from_email:
            raise RuntimeError("В секции [YandexMail] не заполнен параметр from_email.")
        if self.use_ssl and self.use_tls:
            raise RuntimeError(
                "Параметры use_ssl и use_tls одновременно включать нельзя."
            )

    def _connect(self) -> smtplib.SMTP:
        ssl_context = create_default_context()

        if self.use_ssl:
            smtp = smtplib.SMTP_SSL(
                host=self.smtp_host,
                port=self.smtp_port,
                context=ssl_context,
                timeout=20,
            )
        else:
            smtp = smtplib.SMTP(
                host=self.smtp_host,
                port=self.smtp_port,
                timeout=20,
            )
            smtp.ehlo()
            if self.use_tls:
                smtp.starttls(context=ssl_context)
                smtp.ehlo()
        print(self.login, self.password)
        smtp.login(self.login, self.password)
        return smtp

    def send_email(
        self,
        to_email: str,
        subject: str,
        text_body: str,
        html_body: str | None = None,
    ) -> None:
        if not to_email.strip():
            raise ValueError("Получатель письма не указан.")
        if not subject.strip():
            raise ValueError("Тема письма не указана.")
        if not text_body.strip() and not (html_body and html_body.strip()):
            raise ValueError("Текст письма пустой.")

        message = EmailMessage()
        message["Subject"] = subject.strip()
        message["To"] = to_email.strip()
        message["From"] = formataddr((self.from_name, self.from_email))

        if text_body.strip():
            message.set_content(text_body)
        else:
            message.set_content("Ваш почтовый клиент не поддерживает HTML-письма.")

        if html_body and html_body.strip():
            message.add_alternative(html_body, subtype="html")

        with self._connect() as smtp:
            smtp.send_message(message)


def send_yandex_email(
    to_email: str,
    subject: str,
    text_body: str,
    html_body: str | None = None,
) -> None:
    """Удобная обёртка для единичной отправки письма."""

    YandexEmailSender().send_email(
        to_email=to_email,
        subject=subject,
        text_body=text_body,
        html_body=html_body,
    )

if __name__ == "__main__":
    send_yandex_email(
        to_email="597730754a@gmail.com",
        subject="Test",
        text_body="Test",
        html_body="<p>Test</p>",
    )