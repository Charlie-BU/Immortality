from src.database.enums import Gender
from src.services.user import (
    getUserIdByAccessToken,
    getUserById,
    getUserByUsernameOrNicknameOrEmail,
    userLogin,
    userRegister,
    userModifyPassword,
    userBindLark
)

def testUserRegister():
    res = userRegister(
        username="Test",
        password="123456",
        email="test@gmail.com",
        nickname="Test",
        gender=Gender.MALE,
    )
    return res

def testUserLogin():
    res = userLogin(
        username="Test",
        password="123456",
    )
    return res

def testUserBindLark():
    res = userBindLark(
        user_id=1,
        lark_open_id="",
    )
    return res


if __name__ == "__main__":
    print(testUserLogin())
   