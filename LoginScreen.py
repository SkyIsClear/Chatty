# login screen. opened by YK 20/06/2018
import wx
import wx.lib.inspection
import wx.lib.newevent
import wx.lib.scrolledpanel
import datetime
import os
import threading, Queue
import socket, select
import sys
import json
import hashlib
import re

MessageEvent, EVT_MESSAGE = wx.lib.newevent.NewEvent()  # creating custom wx event for notifying wx window when a message is received


class Font_inheritance(object):
    # class to make sure all panels have the fonts
    def __init__(self):
        self.FontBrand = wx.Font(18, wx.ROMAN, wx.ITALIC, wx.NORMAL)
        self.FontEntryFieldLabel = wx.Font(13, wx.MODERN, wx.SLANT, wx.NORMAL)
        self.FontLoginButton = wx.Font(15, wx.MODERN, wx.NORMAL, wx.NORMAL)  # font for login button
        self.FontDoYouAlready = wx.Font(10, wx.DEFAULT, wx.NORMAL, wx.NORMAL)  # for "you have an account already?" etc.
        self.FontEntries = wx.Font(11, wx.DEFAULT, wx.NORMAL, wx.NORMAL)
        self.FontMessage = wx.Font(11, wx.DEFAULT, wx.NORMAL, wx.NORMAL)
        self.FontSendingMessage = wx.Font(15, wx.MODERN, wx.NORMAL, wx.NORMAL)


class LoginPanel(wx.Panel, Font_inheritance):
    def __init__(self, parent, MessagesToSend, MessagesReceived):
        self.parent = parent
        self.MessagesToSend = MessagesToSend
        self.MessagesReceived = MessagesReceived

        self.ForgotWindow = None

        wx.Panel.__init__(self, parent)
        Font_inheritance.__init__(self)  # inheriting all fonts from Font_inheritance
        self.StartOfLabels = 30
        self.Bind(EVT_MESSAGE, self.GotData)

        self.LoginLabel = wx.StaticText(self, label="ChattY - Login", pos=(100, 20), style=wx.ALIGN_CENTER)

        self.LoginLabel.SetFont(self.FontBrand)

        # username label
        self.usrNameLabel = wx.StaticText(self,
                                          label="username:",
                                          pos=(self.StartOfLabels, 70))

        self.usrNameLabel.SetFont(self.FontEntryFieldLabel)
        # entry field for username
        self.usrnameEntry = wx.TextCtrl(self, value="",
                                        size=(137, -1),
                                        pos=(self.StartOfLabels + 95, 70))

        # password label
        self.PasswordLabel = wx.StaticText(self,
                                           label="password:",
                                           pos=(self.StartOfLabels, 110))
        self.PasswordLabel.SetFont(self.FontEntryFieldLabel)
        # password entry field
        self.PasswordEntry = wx.TextCtrl(self,
                                         value="",
                                         size=(135, -1),
                                         pos=(self.StartOfLabels + 97, 110),
                                         style=wx.TE_PASSWORD)

        self.ForgotPasswordButton = wx.Button(self, label='Forgot Password?', pos=(self.StartOfLabels + 100, 130))
        self.ForgotPasswordButton.SetFont(self.FontDoYouAlready)
        self.Bind(wx.EVT_BUTTON, self.ForgotPassword, self.ForgotPasswordButton)

        # Error message static text declaration for later use
        self.ErrorMsg = wx.StaticText(self, label="", pos=(self.StartOfLabels, 135))
        self.ErrorMsg.SetForegroundColour((255, 0, 0))

        # login button declaration
        self.LoginButton = wx.Button(self, label="Log in", pos=(self.StartOfLabels + 100, 150))
        self.LoginButton.SetFont(self.FontLoginButton)

        self.Bind(wx.EVT_BUTTON, self.TryLogin, self.LoginButton)  # binding button press

        self.SignupLabel = wx.StaticText(self, label="Don't have an account yet?", pos=(self.StartOfLabels, 183))
        self.SignupLabel.SetFont(self.FontDoYouAlready)

        # self.SignUpButton_label = wx.StaticText(self, label="Click here to sign up!", pos = (self.StartOfLabels+160, 183))

        self.SignUpButton_button = wx.Button(self, label="Click here to sign up!", pos=(self.StartOfLabels + 159, 180))
        self.SignUpButton_button.SetFont(self.FontDoYouAlready)
        self.SignUpButton_button.SetForegroundColour((0, 0, 255))
        # self.SignUpButton_button.Hide()

        self.Bind(wx.EVT_BUTTON, self.GoSignUp, self.SignUpButton_button)

    def TryLogin(self, event):
        error = self.SendAndCheck(self.usrnameEntry.GetValue(), self.PasswordEntry.GetValue())
        if error:
            self.ErrorMsg.SetLabel(error)

    def SendAndCheck(self, username, password):
        # send to server for checking
        if username and password:
            self.MessagesToSend.put(
                {'opcode': 'login', 'username': username, 'password': str(hashlib.sha256(password).hexdigest())})
            # print "put message in queue",
            return "checking..."
        else:
            return "you did not complete all fields"

    def GoSignUp(self, event):
        self.parent.SignUp()

    def GotData(self, message):
        if message['success'] == 1:  # login was successful
            self.Hide()
            self.parent.StartRooms()
            # print "success"
        else:
            self.ErrorMsg.SetLabel(message['error'])

    def ForgotPassword(self, event):
        self.ForgotWindow = ForgotPassword(self, self.MessagesToSend, self.MessagesReceived)


class SignupPanel(wx.Panel, Font_inheritance):
    def __init__(self, parent, MessagesToSend, MessagesReceived):
        self.parent = parent
        self.MessageToSend = MessagesToSend
        self.MessagesReceived = MessagesReceived

        wx.Panel.__init__(self, parent, wx.ALIGN_CENTER, size=self.parent.GetSize())
        Font_inheritance.__init__(self)

        self.imagesPath = r'C:\Users\YedayaDesktop\chat_rooms'
        self.AvailableImages = ["laughing_emoji.png",
                                "smile_emoji.jpg",
                                "glasses_emoji.png",
                                "heartEyes_emoji.png"]

        for i, img in enumerate(self.AvailableImages):
            self.AvailableImages[i] = os.path.abspath(img)
        # print self.AvailableImages
        self.MainGrid = wx.GridBagSizer(20, 7)
        self.MainGrid.SetEmptyCellSize((0, 0))

        self.labelBorder = 1
        self.EntryBorder = 1

        self.ImageSize = 50
        self.SelectedImage = 0

        self.SignupLabel = wx.StaticText(self, label="Chatty - Sign Up", size=(163, 28))
        self.SignupLabel.SetFont(self.FontBrand)
        self.MainGrid.Add(self.SignupLabel, pos=(0, 0), span=(1, 2), border=self.EntryBorder, flag=wx.ALIGN_CENTER)

        self.MainGrid.Layout()
        self.UsernameLabel = wx.StaticText(self, label="username:")
        self.UsernameLabel.SetFont(self.FontEntryFieldLabel)
        self.MainGrid.Add(self.UsernameLabel, pos=(1, 0), border=self.labelBorder, flag=wx.ALIGN_RIGHT)

        self.UsernameEntry = wx.TextCtrl(self, size=(140, -1), value="")
        self.UsernameEntry.SetFont(self.FontEntries)
        self.MainGrid.Add(self.UsernameEntry, pos=(1, 1), border=self.EntryBorder)

        self.FirstNameLabel = wx.StaticText(self, label="first name:")
        self.FirstNameLabel.SetFont(self.FontEntryFieldLabel)
        self.MainGrid.Add(self.FirstNameLabel, pos=(2, 0), border=self.labelBorder, flag=wx.ALIGN_RIGHT)

        self.FirstNameEntry = wx.TextCtrl(self, size=(140, -1), value="")
        self.FirstNameEntry.SetFont(self.FontEntries)
        self.MainGrid.Add(self.FirstNameEntry, pos=(2, 1))

        self.SurnameLabel = wx.StaticText(self, label="last name:")
        self.SurnameLabel.SetFont(self.FontEntryFieldLabel)
        self.MainGrid.Add(self.SurnameLabel, pos=(3, 0), border=self.labelBorder, flag=wx.ALIGN_RIGHT)

        self.SurnameEntry = wx.TextCtrl(self, size=(140, -1), value="")
        self.SurnameEntry.SetFont(self.FontEntries)
        self.MainGrid.Add(self.SurnameEntry,
                          pos=(3, 1), border=self.EntryBorder)

        self.EmailLabel = wx.StaticText(self,
                                        label="email:")
        self.EmailLabel.SetFont(self.FontEntryFieldLabel)
        self.MainGrid.Add(self.EmailLabel,
                          pos=(4, 0), border=self.labelBorder,
                          flag=wx.ALIGN_RIGHT)

        self.EmailEntry = wx.TextCtrl(self, value="", size=(140, -1), )
        self.EmailEntry.SetFont(self.FontEntries)
        self.MainGrid.Add(self.EmailEntry,
                          pos=(4, 1), border=self.EntryBorder)

        self.BirthLabel = wx.StaticText(self, label="Date of birth:")
        self.BirthLabel.SetFont(self.FontEntryFieldLabel)
        self.MainGrid.Add(self.BirthLabel,
                          pos=(5, 0),
                          border=self.labelBorder,
                          flag=wx.ALIGN_RIGHT)
        self.MainGrid.Layout()
        self.DateSizer = wx.BoxSizer()
        self.DayDrop = wx.ComboBox(self, -1, "1",
                                   size=(35, -1),
                                   choices=[str(x) for x in range(1, 31)],
                                   style=wx.CB_READONLY)
        self.DateSizer.Add(self.DayDrop)
        self.month_lst = ['January', 'February', 'March', 'April', 'May', 'June', 'July',
                          'August', 'September', 'October', 'November', 'December']
        self.MonthDrop = wx.ComboBox(self, -1, self.month_lst[0],
                                     size=(83, -1),
                                     choices=self.month_lst,
                                     style=wx.CB_READONLY)
        self.DateSizer.Add(self.MonthDrop)

        self.YearDrop = wx.ComboBox(self, -1, str(datetime.datetime.now().year),
                                    size=(60, -1),
                                    choices=[str(x) for x in range(int(datetime.datetime.now().year), 1899, -1)],
                                    style=wx.CB_READONLY)
        self.DateSizer.Add(self.YearDrop)
        self.MainGrid.Add(self.DateSizer, pos=(5, 1))
        self.MainGrid.Layout()
        self.ImageLabel = wx.StaticText(self, label="Profile image:")
        self.ImageLabel.SetFont(self.FontEntryFieldLabel)
        self.MainGrid.Add(self.ImageLabel,
                          pos=(6, 0),
                          border=self.labelBorder,
                          flag=wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)

        self.imagesSizer = wx.BoxSizer()

        self.Images = []
        for path in self.AvailableImages:
            self.Images.append(self.Scale(
                wx.Image(path, wx.BITMAP_TYPE_ANY)))

        self.StaticBitmaps = []
        for i, imgPath in enumerate(self.AvailableImages):
            self.StaticBitmaps.append(
                wx.StaticBitmap(self, i, self.Images[i].ConvertToBitmap()))
            self.imagesSizer.Add(self.StaticBitmaps[i])
            self.StaticBitmaps[i].Bind(wx.EVT_LEFT_UP, self.OnImageSelection, self.StaticBitmaps[i])

        self.MainGrid.Add(self.imagesSizer, pos=(6, 1))

        self.PasswordLabel = wx.StaticText(self, label="Password:")
        self.PasswordLabel.SetFont(self.FontEntryFieldLabel)
        self.MainGrid.Add(self.PasswordLabel, pos=(7, 0), flag=wx.ALIGN_RIGHT)

        self.PasswordEntry = wx.TextCtrl(self, value="", size=(140, -1), style=wx.TE_PASSWORD)
        self.MainGrid.Add(self.PasswordEntry, pos=(7, 1))

        self.ConfirmPassLabel = wx.StaticText(self, label="Confirm password:")
        self.ConfirmPassLabel.SetFont(self.FontEntryFieldLabel)
        self.MainGrid.Add(self.ConfirmPassLabel, pos=(8, 0))

        self.ConfirmPassEntry = wx.TextCtrl(self, value="", size=(140, -1), style=wx.TE_PASSWORD)
        self.MainGrid.Add(self.ConfirmPassEntry, pos=(8, 1))

        self.SignupSizer = wx.BoxSizer(wx.VERTICAL)

        self.SignupButton = wx.Button(self, label="Register")
        self.SignupButton.SetFont(self.FontLoginButton)
        self.SignupSizer.Add(self.SignupButton)

        self.Bind(wx.EVT_BUTTON, self.OnRegistration, self.SignupButton)

        self.ErrorLabel = wx.StaticText(self, label="")
        self.ErrorLabel.SetForegroundColour((255, 0, 0))
        self.SignupSizer.Add(self.ErrorLabel)
        # self.MainGrid.Add(self.ErrorLabel, pos=(10, 0), span=(1, 2), flag=wx.ALIGN_CENTER)
        self.MainGrid.Add(self.SignupSizer, pos=(9, 0), span=(1, 2), flag=wx.ALIGN_CENTER)

        self.LoginSizer = wx.BoxSizer(wx.HORIZONTAL)

        self.LoginLabel = wx.StaticText(self, label="Already have an account? ")
        self.LoginLabel.SetFont(self.FontDoYouAlready)
        self.LoginSizer.Add(self.LoginLabel, flag=wx.ALIGN_CENTER_VERTICAL)

        self.LoginButton = wx.Button(self, label="sign in!")
        self.LoginButton.SetFont(self.FontDoYouAlready)
        self.LoginButton.SetForegroundColour((0, 0, 255))

        self.Bind(wx.EVT_BUTTON, self.OnLogin, self.LoginButton)

        self.LoginSizer.Add(self.LoginButton)

        self.MainGrid.Add(self.LoginSizer, pos=(10, 0), span=(1, 2), flag=wx.ALIGN_CENTER)

        self.SetSizerAndFit(self.MainGrid)

    def Scale(self, image, size=""):
        if not size:
            scalingSize = self.ImageSize
        else:
            scalingSize = size
        # scale the image, preserving the aspect ratio
        W = image.GetWidth()
        H = image.GetHeight()
        if W > H:
            NewW = scalingSize
            NewH = scalingSize * H / W
        else:
            NewH = scalingSize
            NewW = scalingSize * W / H
        return image.Scale(NewW, NewH)

    def OnImageSelection(self, event):
        self.SelectedImage = event.GetId()
        for btmp in self.StaticBitmaps:
            if btmp.GetId() == event.GetId():  # this is the image pressed
                btmp.SetBitmap(self.Scale(self.Images[btmp.GetId()]).ConvertToBitmap())
            else:
                btmp.SetBitmap(self.Scale(self.Images[btmp.GetId()], self.ImageSize * 0.85).ConvertToBitmap())
        self.Refresh(False)

    def OnRegistration(self, event):
        # validate on client

        val = Validate()

        UsernameVal = val.username(self.UsernameEntry.GetValue())
        if not UsernameVal[0]:
            self.ErrorLabel.SetLabel(UsernameVal[1])
            return

        PassVal = val.password(self.PasswordEntry.GetValue(), self.ConfirmPassEntry.GetValue())
        if not PassVal[0]:
            self.ErrorLabel.SetLabel(PassVal[1])
            return

        DateVal = val.date(self.YearDrop.GetValue(), self.month_lst.index(self.MonthDrop.GetValue()) + 1,
                           self.DayDrop.GetValue())
        if not DateVal[0]:
            self.ErrorLabel.SetLabel(PassVal[1])

        NameVal = val.Name(self.FirstNameEntry.GetValue(), self.SurnameEntry.GetValue())
        if not NameVal[0]:
            self.ErrorLabel.SetLabel(NameVal[1])
        if self.PasswordEntry.GetValue() == self.ConfirmPassEntry.GetValue():
            self.MessageToSend.put(
                {'opcode': 'register', 'username': self.UsernameEntry.GetValue(), 'email': self.EmailEntry.GetValue(),
                 'firstName': self.FirstNameEntry.GetValue(), 'lastName': self.SurnameEntry.GetValue(),
                 'birthDate': '%s-%s-%s' % (
                     self.YearDrop.GetValue(),
                     self.month_lst.index(self.MonthDrop.GetValue()) + 1,
                     self.DayDrop.GetValue()
                 ),
                 'password': str(hashlib.sha256(self.PasswordEntry.GetValue()).hexdigest()),
                 'image': self.SelectedImage})

    def OnLogin(self, event):
        self.parent.LogIn()

    def GotData(self, message):
        if message['success'] == 1:
            self.parent.StartRooms()
        else:
            self.ErrorLabel.SetLabel(message['error'])
            # print "registration failed"


class ForgotPassword(wx.Frame, Font_inheritance):
    def __init__(self, parent, MessagesToSend, MessageReceived):
        self.parent = parent
        self.MessagesToSend = MessagesToSend
        self.MessageReceived = MessageReceived

        wx.Frame.__init__(self, None, wx.ID_ANY, 'Chatty - chat rooms for you')
        Font_inheritance.__init__(self)

        self.SetBackgroundColour(wx.NullColour)
        self.parent.parent.parent.SetConnectedFrame(self)
        self.Bind(EVT_MESSAGE, self.GotMessage)

        self.MainSizer = wx.BoxSizer(wx.VERTICAL)
        self.UsernameLabel = wx.StaticText(self, label='Enter username:')
        self.UsernameLabel.SetFont(self.FontEntryFieldLabel)
        self.UsernameEntry = wx.TextCtrl(self)
        self.UsernameEntry.SetFont(self.FontEntries)
        self.UsernameSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.UsernameSizer.AddMany([self.UsernameLabel, self.UsernameEntry])

        self.MainSizer.Add(self.UsernameSizer)

        self.EmailSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.EmailLabel = wx.StaticText(self, label='Enter email connected to this account:')
        self.EmailSizer.Add(self.EmailLabel)

        self.EmailEntry = wx.TextCtrl(self, value="")
        self.EmailSizer.Add(self.EmailEntry)

        self.MainSizer.Add(self.EmailSizer)

        self.SendButton = wx.Button(self, label='Send')
        self.MainSizer.Add(self.SendButton)

        self.SetSizer(self.MainSizer)

        self.Bind(wx.EVT_BUTTON, self.OnSend, self.SendButton)
        self.Show(True)

    def OnSend(self, event):
        self.username = self.UsernameEntry.GetValue()
        val = Validate()

        userVal = val.username(self.username)
        if userVal[0]:
            self.MessagesToSend.put(
                {'opcode': 'forgotPassword', 'username': self.username, 'email': self.EmailEntry.GetValue()})

    def GotMessage(self, event):
        message = self.MessageReceived.get()
        if message['opcode'] == 'codeConfirm':
            if message['success'] == 1:
                self.CodeLabel = wx.StaticText(self, label='Enter one-time code:')
                self.CodeEntry = wx.TextCtrl(self)
                self.CodeSizer = wx.BoxSizer(wx.HORIZONTAL)
                self.MainSizer.AddMany([self.CodeLabel, self.CodeEntry])

                self.NewPasswordLabel = wx.StaticText(self, label='New Password:')
                self.NewPasswordLabel.SetFont(self.FontEntryFieldLabel)
                self.NewPasswordEntry = wx.TextCtrl(self)
                self.NewPasswordEntry.SetFont(self.FontEntries)

                self.NewPassSizer = wx.BoxSizer(wx.HORIZONTAL)
                self.NewPassSizer.AddMany([self.NewPasswordLabel, self.NewPasswordEntry])

                self.ConfPasswordLabel = wx.StaticText(self, label='Confirm Password:')
                self.ConfPasswordLabel.SetFont(self.FontEntryFieldLabel)
                self.ConfPasswordEntry = wx.TextCtrl(self)
                self.ConfPasswordEntry.SetFont(self.FontEntries)

                self.ConfPassSizer = wx.BoxSizer(wx.HORIZONTAL)
                self.ConfPassSizer.AddMany([self.ConfPasswordLabel, self.ConfPasswordEntry])

                self.MainSizer.AddMany([self.NewPassSizer, self.ConfPassSizer])

                self.ResetButton = wx.Button(self, label='Set new password')
                self.ResetButton.SetFont(self.FontLoginButton)
                self.MainSizer.Add(self.ResetButton)
                self.Bind(wx.EVT_BUTTON, self.OnReset, self.ResetButton)
                self.Refresh(False)

        elif message['opcode'] == 'resetConfirm':
            self.Destroy()
            self.parent.parent.StartRooms()

    def OnReset(self, event):
        val = Validate()
        passVal = val.password(self.NewPasswordEntry.GetValue(), self.ConfPasswordEntry.GetValue())

        if passVal[0]:
            self.MessagesToSend.put(
                {'opcode': 'resetPassword',
                 'newPassword': str(hashlib.sha256(self.NewPasswordEntry.GetValue()).hexdigest())})


class StartFrame(wx.Frame):
    def __init__(self, parent, connection, MessagesToSend, MessagesReceived):
        wx.Frame.__init__(self, None, wx.ID_ANY, 'Chatty - chat rooms for you', size=(350, 300))

        self.MessagesToSend = MessagesToSend
        self.MessagesReceived = MessagesReceived

        self.parent = parent
        # self.SignupPanel = None

        self.Bind(EVT_MESSAGE, self.GotMessage)

        self.Bind(wx.EVT_CLOSE, self.close)

        self.connection = connection
        # self.SetMaxSize((350, 300))
        self.PanelSizer = wx.BoxSizer()
        self.SetMinSize((350, 300))

        self.SetBackgroundColour(wx.NullColour)

        self.SignupPanel = SignupPanel(self, self.MessagesToSend, self.MessagesReceived)
        self.PanelSizer.Add(self.SignupPanel, wx.ID_ANY, wx.EXPAND | wx.ALIGN_CENTER)
        self.SignupPanel.Hide()
        self.LogIn()

    def LogIn(self):
        self.SetSize((350, 300))
        self.SignupPanel.Hide()
        self.LoginPanel = LoginPanel(self, self.MessagesToSend, self.MessagesReceived)
        self.PanelSizer.Add(self.LoginPanel, wx.ID_ANY, wx.EXPAND)
        self.Layout()
        self.SetTitle("Chatty - Login")
        self.SetSizer(self.PanelSizer)

    def SignUp(self):

        self.LoginPanel.Destroy()
        # self.LoginPanel.Disable()
        # self.SignupPanel = SignupPanel(self, self.MessagesToSend, self.MessagesReceived)
        # self.PanelSizer.Add(self.SignupPanel, wx.ID_ANY, wx.EXPAND | wx.ALIGN_CENTER)
        self.SignupPanel.Show()
        self.SetSize((400, 570))
        # self.SetSizerAndFit(self.PanelSizer)

        # self.Layout()

    def GotMessage(self, event):
        message = self.MessagesReceived.get()
        # print "start frame received message: %s" % message
        action = message['opcode']
        if action == 'loginConfirm':
            self.LoginPanel.GotData(message)
        if action == 'regConfirm':
            self.SignupPanel.GotData(message)

    def close(self, event):
        wx.Window.Destroy(self)
        wx.CallAfter(self.connection.close)

    def StartRooms(self):
        self.parent.LoggedIn()
        self.Destroy()


class MessagesPanel(wx.lib.scrolledpanel.ScrolledPanel, Font_inheritance):
    def __init__(self, parent, size):
        self.size = size
        self.parent = parent
        self.NumMessages = 0

        # print self.size
        # wx.lib.scrolledpanel.__init__(self, self.parent, size=self.size, style=wx.VSCROLL)
        wx.lib.scrolledpanel.ScrolledPanel.__init__(self, self.parent, size=self.size)
        Font_inheritance.__init__(self)
        self.MessagesSizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.MessagesSizer)
        # self.SetBackgroundColour('#112233')

        self.SetupScrolling(scroll_x=False, scroll_y=True)

        # self.AddMessage("toataly random messagte that isn't made up", "RealUser", 2)

    def AddMessage(self, message, sender, image):
        self.NumMessages += 1
        self.NewMessage = wx.StaticText(self, label=sender + ": " + message)
        self.NewMessage.SetFont(self.FontMessage)
        # self.NewMessage.SetForegroundColour('#FFFFFF')
        self.NewMessage.Wrap(self.size[0] - 30)
        self.MessagesSizer.Add(self.NewMessage)
        # print "added message to screen"
        self.MessagesSizer.AddSpacer(5)

        evt = wx.ScrollEvent(wx.EVT_SCROLL_BOTTOM.typeId, self.GetId())
        wx.PostEvent(self.GetEventHandler(), evt)

        # self.GetEventHandler().ProcessEvent(wx.EVT_SCROLL_BOTTOM())
        # print self.GetScrollPos(wx.VERTICAL)
        # print self.NumMessages
        # self.SetScroll
        # if self.NumMessages > 13:
        #     self.SetScrollPos(wx.VERTICAL, self.NumMessages-13)
        # self.SetScrollPos(wx.VERTICAL, self.GetScrollRange(wx.VERTICAL))

        # self.ShowScrollbars(self.GetScrollRange(wx.HORIZONTAL), self.GetScrollRange(wx.VERTICAL))


class Room(wx.Frame, Font_inheritance):
    def __init__(self, connection, MessagesToSend, MessagesReceived, RoomTitle, RoomID):
        self.size = (600, 370)
        self.connection = connection
        self.MessagesToSend = MessagesToSend
        self.MessagesReceived = MessagesReceived
        self.RoomTitle = RoomTitle
        self.RoomID = RoomID

        wx.Frame.__init__(self, None, wx.ID_ANY, 'Chatty - ' + str(self.RoomTitle), size=self.size)
        Font_inheritance.__init__(self)
        self.SetMaxSize(self.size)
        self.SetMinSize(self.size)

        self.Bind(wx.EVT_CLOSE, self.close)
        self.Bind(EVT_MESSAGE, self.GotData)

        self.PanelSizer = wx.BoxSizer(wx.VERTICAL)

        self.messagePanel = MessagesPanel(self, (600, 300))
        self.PanelSizer.Add(self.messagePanel)

        self.entryPanel = wx.Panel(self)

        self.SendSizer = wx.BoxSizer()

        self.SendBox = wx.SearchCtrl(self.entryPanel)
        self.SendBox.ShowCancelButton(False)
        self.SendBox.ShowSearchButton(False)
        self.SendBox.SetDescriptiveText("type a new message")
        self.SendBox.SetMinSize((500, 30))
        self.SendBox.SetFont(self.FontSendingMessage)
        self.SendSizer.Add(self.SendBox)

        self.SendButton = wx.Button(self.entryPanel, label="Send", size=(-1, 30))

        self.Bind(wx.EVT_BUTTON, self.SendMessage, self.SendButton)
        self.Bind(wx.EVT_TEXT_ENTER, self.SendMessage, self.SendBox)
        self.SendSizer.Add(self.SendButton)

        self.entryPanel.SetSizer(self.SendSizer)

        self.PanelSizer.Add(self.entryPanel)

        self.SetSizer(self.PanelSizer)

        self.Show()

    def close(self, event):
        wx.Window.Destroy(self)
        wx.CallAfter(self.connection.close)

    def GotData(self, event):
        # print "got data"
        message = self.MessagesReceived.get()
        # print "message: %s" % message
        if message['opcode'] == 'messageToYou':
            self.messagePanel.AddMessage(message['message'], message['sender'], 2)
            self.Layout()

    def SendMessage(self, event):
        if self.SendBox.GetValue():
            self.MessagesToSend.put({'opcode': 'message', 'room': self.RoomID, 'message': self.SendBox.GetValue()})
            self.SendBox.SetValue("")
            self.SendBox.SetFocus()


class ChooseFrame(wx.Frame):
    def __init__(self, parent, MessagesToSend, MessagesReceived):
        self.MessagesToSend = MessagesToSend
        self.MessagesReceived = MessagesReceived
        self.parent = parent
        self.room = "Sport room"  # deafault room
        self.RoomID = 0
        wx.Frame.__init__(self, None, wx.ID_ANY, 'Chatty - chat rooms for you')

        self.Bind(EVT_MESSAGE, self.GotData)

        self.PanelSizer = wx.GridBagSizer()
        self.SportLabel = wx.Button(self, id=0, label="Sport", size=(200, 70))
        self.PanelSizer.Add(self.SportLabel, pos=(0, 0))
        self.Bind(wx.EVT_BUTTON, self.Choose, self.SportLabel)

        self.GamingLabel = wx.Button(self, id=1, label="Gaming", size=(200, 70))
        self.PanelSizer.Add(self.GamingLabel, pos=(0, 1))
        self.Bind(wx.EVT_BUTTON, self.Choose, self.GamingLabel)

        self.FoodLabel = wx.Button(self, id=2, label="Food", size=(200, 70))
        self.PanelSizer.Add(self.FoodLabel, pos=(1, 0))
        self.Bind(wx.EVT_BUTTON, self.Choose, self.FoodLabel)

        self.MoviesLabel = wx.Button(self, id=3, label="Movies", size=(200, 70))
        self.PanelSizer.Add(self.MoviesLabel, pos=(1, 1))
        self.Bind(wx.EVT_BUTTON, self.Choose, self.MoviesLabel)

        self.SetSizer(self.PanelSizer)

        self.Show()

    def Choose(self, event):
        self.RoomID = event.GetId()
        if self.RoomID == 0:
            self.room = "Sports room"
        elif self.RoomID == 1:
            self.room = "Gaming room"
        elif self.RoomID == 2:
            self.room = "Food room"
        else:
            self.room = "Movies room"

        self.MessagesToSend.put({'opcode': 'joinRoom', 'roomID': event.GetId()})

    def GotData(self, event):
        message = self.MessagesReceived.get()
        if message['opcode'] == 'roomConfirm':
            if message['success'] == 1:
                self.parent.PickedRoom(self.room, self.RoomID)
                self.Destroy()


class ServerConnection(threading.Thread):
    def __init__(self, MessagesToSend, MessagesReceived, connectedFrame=None, IP='127.0.0.1', PORT=35628):
        threading.Thread.__init__(self)
        # print "thread initiated"
        self.IP = IP
        self.PORT = PORT
        self.running = 0
        self.MessagesToSend = MessagesToSend
        self.MessagesReceived = MessagesReceived
        self.connectedFrame = connectedFrame

    def run(self):
        self.running = 1
        self.Socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.Socket.connect((self.IP, self.PORT))
        try:
            while self.running:
                rlist, wlist, xlist = select.select([self.Socket], [self.Socket], [])
                if rlist:  # checking if server is sending data
                    msg = self.Socket.recv(8192)
                    # print msg
                    if msg:
                        # print "raw Message: %s" % msg
                        messages = msg.split('}{')
                        for message in messages:
                            decodedMsg = json.loads('{' + message + '}') if len(messages) > 1 else json.loads(
                                message)  # decoding message
                            self.MessagesReceived.put(decodedMsg)  # once lock was acquired appends message
                            wx.PostEvent(self.connectedFrame, MessageEvent())
                            # print "posted event"
                    else:
                        print "server disconnected"
                        self.Socket.close()
                        self.running = False
                        sys.exit()
                if wlist:  # checking if server is ready for data
                    while not self.MessagesToSend.empty():
                        msg = self.MessagesToSend.get()
                        # print "sending message: %s" % msg
                        encodedMsg = json.dumps(msg, separators=(',', ':'))  # encoding message before delivery
                        # print "encoded message: %s" % encodedMsg
                        self.Socket.send(encodedMsg)
            self.Socket.close()
        except Exception as error:
            if "errno" in error:
                # print "error" + str(error) + "line: %d" % sys.exc_info()[-1].tb_lineno
                self.Socket.close()
            else:
                raise

    def SetFrame(self, frame):
        # print "set frame to %s" % frame
        self.connectedFrame = frame

    def close(self):
        # print "closing thread and connection..."
        self.MessagesToSend.put({'opcode': 'logout'})
        # self.running = False


class MyApp(wx.App):  # main app, opens all frames when needed and controls were server connection sends its data
    def __init__(self):
        wx.App.__init__(self)
        self.MessagesTosend = Queue.Queue()
        self.MessagesReceived = Queue.Queue()

        self.connection = ServerConnection(self.MessagesTosend, self.MessagesReceived, connectedFrame=self)
        self.connection.start()

        self.InitUI()
        self.MainLoop()

    def InitUI(self):
        self.StartFrame = StartFrame(self, self.connection, self.MessagesTosend, self.MessagesReceived)
        wx.CallAfter(self.connection.SetFrame, self.StartFrame)
        self.StartFrame.Show(True)

    def LoggedIn(self):  # log in was successful
        self.Choose = ChooseFrame(self, self.MessagesTosend, self.MessagesReceived)
        wx.CallAfter(self.connection.SetFrame, self.Choose)

    def PickedRoom(self, title, roomID):
        self.Room = Room(self.connection, self.MessagesTosend, self.MessagesReceived, title, roomID)
        wx.CallAfter(self.connection.SetFrame, self.Room)

    def SetConnectedFrame(self, frame):
        wx.CallAfter(self.connection.SetFrame, frame)


class Validate(object):
    def username(self, name):
        if not name:
            return False, 'You did not complete all fields'
        try:
            name.decode('ascii')
            if len(name) < 5:
                return False, 'username is too short'
            return True, ''
        except:
            return False, 'username contains non-ascii characters'

    def password(self, word, confirmWord):
        if not word or not confirmWord:
            return False, 'You did not complete all fields'
        if word != confirmWord:
            return False, 'passwords do not match'
        if len(word) < 8:
            return False, 'password is too short'
        if not re.search(r'\d', word):
            return False, 'password must contain at least 1 digit'
        if not bool(re.match(r'(?=.*[a-zA-Z])', 'a4354')):
            return False, 'password must contain at least one letter'
        return True, ''

    def date(self, year, month, day):
        # print 'year: %s, month: %s, day: %s' % (year, month, day)
        if self.calculateAge(datetime.date(int(year), int(month), int(day))) < 14:
            return False, 'you must be 14 years old to use this product'
        return True, ''

    def Name(self, first, last):
        if not first or not last:
            return False, 'You did not complete all fields'
        if not re.search(r'[^\.a-zA-Z]', first):
            return False, 'name must contain only letters'
        if not re.search(r'[^\.a-zA-Z]', last):
            return False, 'name must contain only letters'
        if len(first) < 2 or len(last) < 2:
            return False, 'name is invalid'

    def calculateAge(self, born):
        today = datetime.date.today()
        a = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
        # print a
        return a


def main():
    App = MyApp()
    # queues that are used to share messages across threads
    # MessagesTosend = Queue.Queue()
    # MessagesReceived = Queue.Queue()
    #
    # Connection = ServerConnection(MessagesTosend, MessagesReceived)
    #
    # app = wx.App(False)
    # frame = StartFrame(Connection, MessagesTosend, MessagesReceived)
    #
    # Connection.SetFrame(frame)
    # Connection.start()
    # frame.Show()
    # # wx.lib.inspection.InspectionTool().Show()
    # app.MainLoop()


if __name__ == "__main__":
    main()  # self.SignupPanel.Show()
