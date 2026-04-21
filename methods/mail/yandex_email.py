from __future__ import annotations

import smtplib
from email.message import EmailMessage
from typing import Iterable

from config_loader import read_config


class YandexEmailSender:
    DEFAULT_HOST = "smtp.yandex.ru"
    DEFAULT_PORT = 465
    CONFIG_SECTION = "YandexEmail"

    def __init__(self) -> None:
        config = read_config()

        if not config.has_section(self.CONFIG_SECTION):
            raise RuntimeError(
                "В config.ini нет секции [YandexEmail]. "
                "Добавьте login, password и при необходимости sender_email."
            )

        section = config[self.CONFIG_SECTION]
        self.host = section.get("host", self.DEFAULT_HOST).strip()
        self.port = section.getint("port", self.DEFAULT_PORT)
        self.login = section.get("login", "").strip()
        self.password = section.get("password", "").strip()
        self.sender_email = section.get("sender_email", self.login).strip()
        self.sender_name = section.get("sender_name", "").strip()
        self.use_ssl = section.getboolean("use_ssl", fallback=self.port == 465)
        self.use_tls = section.getboolean("use_tls", fallback=not self.use_ssl)
        self.timeout = section.getint("timeout", fallback=10)

        if not self.login or not self.password:
            raise RuntimeError(
                "Для отправки почты через Yandex нужны параметры "
                "[YandexEmail] login и password."
            )

        if not self.sender_email:
            raise RuntimeError(
                "Не удалось определить email отправителя. "
                "Укажите [YandexEmail] sender_email или login."
            )

    def _build_message(
        self,
        to_email: str,
        subject: str,
        body: str,
        html_body: str | None = None,
    ) -> EmailMessage:
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = (
            f"{self.sender_name} <{self.sender_email}>"
            if self.sender_name
            else self.sender_email
        )
        message["To"] = to_email
        message.set_content(body)

        if html_body:
            message.add_alternative(html_body, subtype="html")

        return message

    def send_message(
        self,
        to_email: str,
        subject: str,
        body: str,
        html_body: str | None = None,
    ) -> None:
        message = self._build_message(to_email, subject, body, html_body)

        if self.use_ssl:
            with smtplib.SMTP_SSL(
                self.host,
                self.port,
                timeout=self.timeout,
            ) as smtp:
                smtp.login(self.login, self.password)
                smtp.send_message(message)
            return

        with smtplib.SMTP(self.host, self.port, timeout=self.timeout) as smtp:
            smtp.ehlo()
            if self.use_tls:
                smtp.starttls()
                smtp.ehlo()
            smtp.login(self.login, self.password)
            smtp.send_message(message)

    def send_messages(
        self,
        to_emails: Iterable[str],
        subject: str,
        body: str,
        html_body: str | None = None,
    ) -> None:
        for to_email in to_emails:
            self.send_message(
                to_email=to_email,
                subject=subject,
                body=body,
                html_body=html_body,
            )
