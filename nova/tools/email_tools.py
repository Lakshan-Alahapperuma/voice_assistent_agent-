import subprocess
from typing import Dict, Any, Optional
from nova.tools.base import BaseTool

class DraftEmailTool(BaseTool):
    name = "draft_email"
    description = "Drafts an email with a recipient, subject, and body, opening it in macOS Mail or preparing it for review."
    parameters = {
        "type": "object",
        "properties": {
            "recipient": {
                "type": "string",
                "description": "Recipient email address or contact name."
            },
            "subject": {
                "type": "string",
                "description": "Subject line of the email."
            },
            "body": {
                "type": "string",
                "description": "Content/body of the email."
            },
            "open_in_mail_app": {
                "type": "boolean",
                "description": "Whether to open the draft directly in macOS Mail app for user inspection (default: true)."
            }
        },
        "required": ["recipient", "subject", "body"]
    }

    def execute(self, recipient: str, subject: str, body: str, open_in_mail_app: bool = True) -> Dict[str, Any]:
        draft = {
            "recipient": recipient,
            "subject": subject,
            "body": body,
            "status": "drafted"
        }

        if open_in_mail_app:
            # Escape strings for AppleScript
            escaped_subject = subject.replace('\\', '\\\\').replace('"', '\\"')
            escaped_body = body.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
            escaped_to = recipient.replace('\\', '\\\\').replace('"', '\\"')

            applescript = f'''
            tell application "Mail"
                set newMsg to make new outgoing message with properties {{subject:"{escaped_subject}", content:"{escaped_body}", visible:true}}
                tell newMsg
                    make new to recipient at end of to recipients with properties {{address:"{escaped_to}"}}
                end tell
                activate
            end tell
            '''
            try:
                res = subprocess.run(["osascript", "-e", applescript], capture_output=True, text=True, check=False)
                if res.returncode == 0:
                    draft["mail_app_opened"] = True
                else:
                    draft["mail_app_opened"] = False
                    draft["mail_app_error"] = res.stderr.strip()
            except Exception as e:
                draft["mail_app_opened"] = False
                draft["mail_app_error"] = str(e)

        return {
            "status": "success",
            "message": f"Draft created for {recipient} with subject '{subject}'.",
            "draft": draft
        }

class SendEmailTool(BaseTool):
    name = "send_email"
    description = "Sends an email after explicit user approval. Operates via macOS Mail application."
    requires_confirmation = True
    parameters = {
        "type": "object",
        "properties": {
            "recipient": {
                "type": "string",
                "description": "Recipient email address."
            },
            "subject": {
                "type": "string",
                "description": "Email subject."
            },
            "body": {
                "type": "string",
                "description": "Email message body."
            }
        },
        "required": ["recipient", "subject", "body"]
    }

    def execute(self, recipient: str, subject: str, body: str) -> Dict[str, Any]:
        escaped_subject = subject.replace('\\', '\\\\').replace('"', '\\"')
        escaped_body = body.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
        escaped_to = recipient.replace('\\', '\\\\').replace('"', '\\"')

        applescript = f'''
        tell application "Mail"
            set newMsg to make new outgoing message with properties {{subject:"{escaped_subject}", content:"{escaped_body}", visible:false}}
            tell newMsg
                make new to recipient at end of to recipients with properties {{address:"{escaped_to}"}}
                send
            end tell
        end tell
        '''
        try:
            res = subprocess.run(["osascript", "-e", applescript], capture_output=True, text=True, check=False)
            if res.returncode == 0:
                return {
                    "status": "sent",
                    "recipient": recipient,
                    "subject": subject,
                    "message": f"Email successfully sent to {recipient}."
                }
            else:
                return {
                    "status": "error",
                    "error": f"macOS Mail error: {res.stderr.strip()}"
                }
        except Exception as e:
            return {"status": "error", "message": f"Failed to send email: {str(e)}"}
