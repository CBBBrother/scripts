package main

import (
    "fmt"
	"log"
	"strings"
	"sync"
	"time"

	"github.com/emersion/go-imap"
	imapclient "github.com/emersion/go-imap/client"
	tgbotapi "github.com/go-telegram-bot-api/telegram-bot-api/v5"
)

type EmailUser struct {
    Email string
    Password string
}

func login_user(email string, password string) (*imapclient.Client, error) {
    log.Printf("login user: %s %s ", email, password)

    c, err := imapclient.Dial("localhost:143")
	if err != nil {
		log.Fatal(err)
        return nil, err
	}

    err = c.Login(email, password)
    if err != nil {
        log.Panic(err)
        return nil, err
    }

    return c, nil
}

func fetch(user *EmailUser) []string {
    c, err := login_user(user.Email, user.Password)
	if err != nil {
        log.Println(err)
        return []string{}
	}

    log.Println("Connected")
    defer c.Logout()

    _, err = c.Select("INBOX", false)
    if err != nil {
        log.Println(err)
        return []string{}
    }
    log.Println("Selected INBOX")

    criteria := imap.NewSearchCriteria()
    criteria.WithoutFlags = []string{"\\Seen"}
    uids, err := c.Search(criteria)
    if err != nil {
        log.Println(err)
        return []string{}
    }

    seqset := new(imap.SeqSet)
    seqset.AddNum(uids...)
    items := []imap.FetchItem{imap.FetchEnvelope}
    messages := make(chan *imap.Message)
    done := make(chan error, 1)
    go func() {
        done <- c.Fetch(seqset, items, messages)
    }()

    emails := make([]string, 0, len(uids))
    for msg := range messages {
        log.Println(msg.Envelope.Subject)
        emails = append(emails, fmt.Sprintf("%s - %s", msg.Envelope.From[0].PersonalName, msg.Envelope.Subject))
    }

    // mark seen messages
    seenFlagItem := imap.FormatFlagsOp(imap.AddFlags, true)
    flags := []interface{}{imap.SeenFlag}
    err = c.Store(seqset, seenFlagItem, flags, nil)
    if err != nil {
        log.Println(err)
    }

    return emails
}

func main() {
    users := map[int64]EmailUser{}
    mu := sync.Mutex{}

    bot, err := tgbotapi.NewBotAPI("")
    if err != nil {
        log.Panic(err)
    }

    bot.Debug = true
    
    log.Printf("Authorized on account %s", bot.Self.UserName)

    u := tgbotapi.NewUpdate(0)
    u.Timeout = 60

    updates := bot.GetUpdatesChan(u)

    go func(users* map[int64]EmailUser) {
        for {
            mu.Lock()

            log.Println("Go checking emails")
            for chatId, email := range *users {
                letters := fetch(&email)
                if len(letters) == 0 {
                    continue
                }
                reply := strings.Join(letters, "\n")
                msg := tgbotapi.NewMessage(chatId, reply)
                bot.Send(msg)
            }

            mu.Unlock()
            time.Sleep(1 * time.Minute)
        }
    }(&users)

    for update := range updates {
        if update.Message != nil {
            chatId := update.Message.Chat.ID
            if update.Message.IsCommand() {
                switch update.Message.Command() {
                case "set_check_email":
                    args := strings.Split(update.Message.CommandArguments(), " ")
                    if len(args) != 2 {
                        continue
                    }
                    
                    _, ok := users[chatId]
                    if ok {
                        continue
                    }

                    c, err := login_user(args[0], args[1])
                    c.Logout()

                    if err == nil {
                        mu.Lock()
                        users[chatId] = EmailUser{args[0], args[1]}
                        mu.Unlock()
                        msg := tgbotapi.NewMessage(chatId, "Done!")
                        msg.ReplyToMessageID = update.Message.MessageID
                        bot.Send(msg)
                    }
                }
            } else if len(update.Message.Text) > 0 {
                var reply string
                mu.Lock()
                _, ok := users[chatId]
                mu.Unlock()
                if ok {
                    reply = "You are already subscribed to mail!"
                } else {
                    reply = "You aren't subscribed!"
                }

                msg := tgbotapi.NewMessage(update.Message.Chat.ID, reply)
                bot.Send(msg)
            }
        }
    }
}
