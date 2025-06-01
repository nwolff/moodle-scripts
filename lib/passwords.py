"""
We want new users to login with eduvaud and not their moodle login.

For both teachers and students we create new users by uploading csv files,
Options for the password are described here https://docs.moodle.org/404/en/Upload_users#Passwords
- Leaving the password empty would generate a password automatically and send an email to the user
- Setting the password to "changeme" would let anyone on the internet who can guess usernames login.

So our only option is to generate an impossible to guess password.
We generate the password from the email so we have repeatability when we run the script

The password rules that are enforced as on 2024-06-25 are here :
https://moodle.gymnasedebeaulieu.ch/admin/settings.php?section=sitepolicies

- 8 characters min
- At least one digit
- At least one lowercase character

"""

import hashlib


def password_generator(salt: str):
    def password_from_email(email: str) -> str:
        salted_input = (salt + email).encode("utf-8")

        # this will contain a number with high probability, we just make sure it does
        return hashlib.sha256(salted_input).hexdigest()[:32] + "1"

    return password_from_email
