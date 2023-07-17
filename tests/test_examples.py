from email.message import EmailMessage, Message
from smtplib import SMTP
from typing import NoReturn, Union

from smtpdfix.controller import AuthController


class Test_Examples:
    '''
    Tests intended as examples for common scenarios.
    '''

    def test_email_headers_and_body(self, smtpd: AuthController) -> NoReturn:
        '''
        Get email headers and body once received.
        '''

        def _get_body(
                message: Union[Message, EmailMessage]
                ) -> Union[bytes, None, str]:
            '''
            Helper method to extract the body from an email message.
            '''

            if isinstance(message, EmailMessage):
                body = message.get_body()
                if body is not None:
                    return body.get_payload(decode=True)
                return body  # returns if the body is None
            else:
                if message.is_multipart():
                    # handle a multipart message
                    for part in message.walk():
                        dispo = part.get_content_disposition()
                        if (part.get_content_type() == "text/plain" and
                                dispo != "attachment"):
                            return part.get_payload(decode=True)

                return message.get_payload(decode=True)

        # Generate an email.message.EmailMessage to send
        sender = "from@example.org"
        to = ["recipient1@example.org", "recipient2@example.org"]
        subject = "This is an email"
        content = "This is plain text email body"

        msg = EmailMessage()
        msg["Sender"] = sender
        msg["Reply-To"] = sender
        msg["To"] = ", ".join(to)
        msg["Subject"] = subject
        msg.set_content(content)

        # Send the message using smtplib.SMTP
        with SMTP(smtpd.hostname, smtpd.port) as client:
            client.send_message(msg)

        # Ensure we have received only one message!
        assert len(smtpd.messages) == 1

        # Test that the message is as expected.
        for rcvd in smtpd.messages:
            assert rcvd["Sender"] == msg["Sender"]
            assert rcvd["Reply-To"] == sender
            body = _get_body(rcvd)
            if isinstance(body, bytes):
                body = body.decode()
            assert content in body
