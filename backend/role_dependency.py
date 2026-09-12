from fastapi import Depends, HTTPException
from auth_dependency import get_current_user


def require_role(required_role: str):
    def role_checker(current_user=Depends(get_current_user)):
        if current_user["role"] != required_role:
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to perform this action"
            )

        return current_user

    return role_checker