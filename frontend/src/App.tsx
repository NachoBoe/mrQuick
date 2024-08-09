import React, { useState, useEffect, useRef } from 'react';
import styled from 'styled-components';
import yaml from 'js-yaml';

interface Activity {
  type: string;
  content: string;
  timestamp: string;
  sender: string;
  card_content?: string;
  suggestion_content?: string[];
}

class FillIn {
  constructor(
    public id: string,
    public input_type: 'number' | 'string',
    public label: string,
    public required: boolean = false,
    public defaultValue: string = ''
  ) {}
}

class Choice {
  constructor(
    public id: string,
    public options: { title: string; value: string }[],
    public label: string,
    public required: boolean = false,
    public defaultValue: string = ''
  ) {}
}

class ButtonAd {
  constructor(public id: string, public actions: string[], public label: string) {}
}

class TextAd {
  constructor(public id: string, public text: string) {}
}

const App: React.FC = () => {
  const [messages, setMessages] = useState<Activity[]>([]);
  const [message, setMessage] = useState<string>('');
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const ws = useRef<WebSocket | null>(null);
  const [formData, setFormData] = useState<{ [key: string]: any }>({});
  const [isSubmitEnabled, setIsSubmitEnabled] = useState<{ [key: string]: boolean }>({});
  const [isCardLocked, setIsCardLocked] = useState<{ [key: string]: boolean }>({});
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    ws.current = new WebSocket('ws://localhost:8000/ws');

    ws.current.onmessage = (event) => {
      const activity: Activity = JSON.parse(event.data);
      if (activity.type === 'suggestion' && activity.suggestion_content) {
        setSuggestions(activity.suggestion_content);
      } else {
        setMessages((prevMessages) => [...prevMessages, activity]);
      }
    };

    return () => {
      ws.current?.close();
    };
  }, []);

  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  // Initialize form data with default values when a new adaptive card is received
  useEffect(() => {
    messages.forEach((msg, index) => {
      if (msg.type === 'adaptive_card' && msg.card_content) {
        const cardElements = parseAdaptiveCard(msg.card_content);
        setFormData((prevData) => {
          if (!prevData[index]) {
            const defaults = cardElements.reduce((acc, element) => {
              if (element instanceof FillIn || element instanceof Choice) {
                acc[element.id] = element.defaultValue;
              }
              return acc;
            }, {} as { [key: string]: any });

            // Check initial validity
            const isInitialValid = checkFormValidity(cardElements, defaults);
            setIsSubmitEnabled((prevState) => ({ ...prevState, [index]: isInitialValid }));

            return { ...prevData, [index]: defaults };
          }
          return prevData;
        });
      }
    });
  }, [messages]);

  const sendMessage = (content: string) => {
    if (ws.current && content) {
      const activity: Activity = {
        type: 'message',
        content,
        timestamp: new Date().toISOString(),
        sender: 'client',
      };
      ws.current.send(JSON.stringify(activity));
      setMessages((prevMessages) => [...prevMessages, activity]);
      setMessage('');
      setSuggestions([]); // Clear suggestions
    }
  };

  const handleSubmit = (id: string) => {
    if (ws.current) {
      const activity: Activity = {
        type: 'adaptive_card_answer',
        content: JSON.stringify(formData[id]), // Send all form data including defaults
        timestamp: new Date().toISOString(),
        sender: 'client',
      };
      ws.current.send(JSON.stringify(activity));
      setIsCardLocked((prevState) => ({ ...prevState, [id]: true }));
      setSuggestions([]); // Clear suggestions
    }
  };

  const renderAdaptiveCard = (cardContent: string, cardId: string) => {
    const cardElements = parseAdaptiveCard(cardContent);

    return (
      <CardContainer>
        {cardElements.map((element, index) => {
          if (element instanceof FillIn) {
            return (
              <div key={index}>
                <Label>
                  {element.label}
                  {element.required && <RequiredAsterisk>*</RequiredAsterisk>}
                </Label>
                <Input
                  type={element.input_type}
                  placeholder={element.id}
                  required={element.required}
                  defaultValue={element.defaultValue}
                  disabled={isCardLocked[cardId]}
                  onChange={(e) =>
                    handleInputChange(cardId, element.id, e.target.value, element.required)
                  }
                />
              </div>
            );
          } else if (element instanceof Choice) {
            return (
              <div key={index}>
                <Label>
                  {element.label}
                  {element.required && <RequiredAsterisk>*</RequiredAsterisk>}
                </Label>
                <Select
                  required={element.required}
                  defaultValue={element.defaultValue}
                  disabled={isCardLocked[cardId]}
                  onChange={(e) =>
                    handleInputChange(cardId, element.id, e.target.value, element.required)
                  }
                >
                  <option value=''>Seleccionar una opción</option>
                  {element.options.map((option, idx) => (
                    <option key={idx} value={option.value}>
                      {option.title}
                    </option>
                  ))}
                </Select>
              </div>
            );
          } else if (element instanceof ButtonAd) {
            return (
              <SubmitButton
                key={index}
                onClick={() => handleSubmit(cardId)}
                disabled={!isSubmitEnabled[cardId] || isCardLocked[cardId]}
              >
                {element.label}
              </SubmitButton>
            );
          } else if (element instanceof TextAd) {
            return <Text key={index}>{element.text}</Text>;
          }
          return null;
        })}
      </CardContainer>
    );
  };

  const handleInputChange = (cardId: string, id: string, value: any, required: boolean) => {
    console.log(required)
    setFormData((prevData) => ({
      ...prevData,
      [cardId]: { ...prevData[cardId], [id]: value },
    }));

    const cardElements = parseAdaptiveCard(messages[parseInt(cardId)].card_content!);
    const updatedFormData = { ...formData[cardId], [id]: value };
    const isFormValid = checkFormValidity(cardElements, updatedFormData);
    setIsSubmitEnabled((prevState) => ({ ...prevState, [cardId]: isFormValid }));
  };

  const checkFormValidity = (elements: (FillIn | Choice | ButtonAd | TextAd)[], data: { [key: string]: any }) => {
    return elements.every((element) => {
      if (element instanceof FillIn || element instanceof Choice) {
        if (element.required) {
          const value = data[element.id];
          return value && value !== '' && value !== 'Seleccionar una opción';
        }
      }
      return true;
    });
  };

  return (
    <AppContainer>
      <ChatContainer>
        <ChatHeader>MrQuick</ChatHeader>
        <MessagesContainer>
          {messages.map((msg, index) => (
            <div key={index}>
              <SenderLabel>{msg.sender === 'client' ? 'Tú' : 'MrQuick'}</SenderLabel>
              <Message sender={msg.sender}>
                {msg.content.split('\n').map((line, i) => (
                  <React.Fragment key={i}>
                    {line}
                    <br />
                  </React.Fragment>
                ))}
                {msg.type === 'adaptive_card' && msg.card_content && renderAdaptiveCard(msg.card_content, `${index}`)}
              </Message>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </MessagesContainer>
        {suggestions.length > 0 && (
          <SuggestionsContainer>
            {suggestions.map((suggestion, index) => (
              <SuggestionButton key={index} onClick={() => sendMessage(suggestion)}>
                {suggestion}
              </SuggestionButton>
            ))}
          </SuggestionsContainer>
        )}
        <MessageForm onSubmit={(e) => { e.preventDefault(); sendMessage(message); }}>
          <MessageInput
            type='text'
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder='Escribe tu mensaje...'
          />
          <SendButton type='submit' />
        </MessageForm>
      </ChatContainer>
    </AppContainer>
  );
};

const parseAdaptiveCard = (cardContent: string): any[] => {
  const parsed = yaml.load(cardContent) as any[];
  return parsed.map((item: any) => {
    if (item.FillIn) {
      return new FillIn(
        item.FillIn.id,
        item.FillIn.input_type,
        item.FillIn.label,
        item.FillIn.required,
        item.FillIn.default || ''
      );
    } else if (item.Choice) {
      return new Choice(
        item.Choice.id,
        item.Choice.options,
        item.Choice.label,
        item.Choice.required,
        item.Choice.default || ''
      );
    } else if (item.ButtonAd) {
      return new ButtonAd(item.ButtonAd.id, item.ButtonAd.actions, item.ButtonAd.label);
    } else if (item.TextAd) {
      return new TextAd(item.TextAd.id, item.TextAd.text);
    }
    return null;
  });
};

const AppContainer = styled.div`
  display: flex;
  justify-content: center;
  align-items: center;
  width: 100vw;
  height: 100vh;
  background-color: #000; /* Black background for border effect */
  padding: 16px; /* To create space for the thick border */
  box-sizing: border-box;
`;

const ChatContainer = styled.div`
  display: flex;
  flex-direction: column;
  width: 100%;
  max-width: 600px; /* Adjusted max-width for 3:4 aspect ratio */
  height: 100%;
  aspect-ratio: 3 / 4;
  border-radius: 30px; /* Rounded corners */
  overflow: hidden;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  background: linear-gradient(135deg, #1c1c1e 40%, #2c2c2e 100%); /* Marbled background */
  border: 6px solid black; /* Thick black border for phone effect */
`;

const ChatHeader = styled.div`
  background-color: transparent;
  color: white;
  padding: 16px;
  font-size: 1.8em;
  font-weight: bold;
  text-align: center;
  font-family: 'Cinzel', serif;
  margin-bottom: 24px; /* Larger margin for spacing */
`;

const MessagesContainer = styled.ul`
  flex: 1;
  padding: 16px;
  overflow-y: auto;
  list-style: none;
  margin: 0;
  width: 100%;
  scrollbar-width: none;
  -ms-overflow-style: none;
  &::-webkit-scrollbar {
    display: none;
  }
`;

const Message = styled.li<{ sender: string }>`
  background-color: ${({ sender }) => (sender === 'client' ? '#4a00e0' : '#333')}; /* More intense blue-violet for user */
  color: ${({ sender }) => (sender === 'client' ? 'white' : '#ddd')};
  padding: 12px;
  margin-bottom: 12px;
  border-radius: ${({ sender }) =>
    sender === 'client' ? '20px 0px 20px 20px' : '0px 20px 20px 20px'}; /* Squared corner for message direction */
  max-width: 80%;
  min-width: 30%;
  width: fit-content;
  word-break: break-word;
  text-align: ${({ sender }) => (sender === 'client' ? 'right' : 'left')};
  margin-left: ${({ sender }) => (sender === 'client' ? 'auto' : '16px')};
  margin-right: ${({ sender }) => (sender === 'client' ? '16px' : 'auto')};
  white-space: pre-wrap;
  box-shadow: 0px 2px 4px rgba(0, 0, 0, 0.1);
  font-weight: bold; /* Thicker text */
`;

const SenderLabel = styled.span`
  display: block;
  font-weight: bold;
  margin-bottom: 4px;
  color: #888;
  text-align: ${({ children }) => (children === 'Tú' ? 'right' : 'left')};
  margin-left: ${({ children }) => (children === 'Tú' ? 'auto' : '16px')};
  margin-right: ${({ children }) => (children === 'Tú' ? '16px' : 'auto')};
  max-width: 80%;
  min-width: 30%;
  width: fit-content;
`;

const SuggestionsContainer = styled.div`
  display: flex;
  justify-content: center;
  flex-wrap: wrap;
  padding: 8px 16px;
  background: linear-gradient(135deg, #1c1c1e 40%, #2c2c2e 100%);
  border-top: 1px solid #444;
`;

const SuggestionButton = styled.button`
  background-color: #555;
  color: white;
  border: none;
  padding: 8px 16px;
  margin: 4px;
  border-radius: 20px;
  cursor: pointer;
  transition: background-color 0.3s;
  &:hover {
    background-color: #444;
  }
`;

const MessageForm = styled.form`
  display: flex;
  padding: 16px;
  border-top: 1px solid #444;
  background: linear-gradient(135deg, #1c1c1e 40%, #2c2c2e 100%);
`;

const MessageInput = styled.input`
  flex: 1;
  padding: 12px;
  border: none;
  border-radius: 20px;
  margin-right: 8px;
  background-color: #444;
  color: white;
  &::placeholder {
    color: #aaa;
  }
  &:focus {
    outline: none;
  }
`;

const SendButton = styled.button`
  background-color: #0078d4;
  color: white;
  border: none;
  padding: 12px;
  border-radius: 50%;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background-color 0.3s;
  &:hover {
    background-color: #005a9e;
  }
  &::before {
    content: '➤';
    font-size: 16px;
  }
`;

const CardContainer = styled.div`
  background-color: #3a3a3a;
  padding: 16px;
  border: 1px solid #555;
  border-radius: 12px;
  margin-top: 12px;
  color: white;
`;

const Input = styled.input`
  width: 100%;
  padding: 8px;
  margin-bottom: 8px;
  border: 1px solid #444;
  border-radius: 8px;
  background-color: #555;
  color: white;
`;

const Select = styled.select`
  width: 100%;
  padding: 8px;
  margin-bottom: 8px;
  border: 1px solid #444;
  border-radius: 8px;
  background-color: #555;
  color: white;
`;

const Text = styled.p`
  margin-bottom: 8px;
  color: #ddd;
`;

const Label = styled.label`
  display: block;
  margin-bottom: 4px;
  color: #ddd;
`;

const RequiredAsterisk = styled.span`
  color: red;
  margin-left: 4px;
`;

const SubmitButton = styled.button`
  background-color: #0078d4;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 8px;
  cursor: pointer;
  margin-top: 8px;
  transition: background-color 0.3s;
  &:hover {
    background-color: #005a9e;
  }
  &:disabled {
    background-color: #777;
    cursor: not-allowed;
  }
`;

export default App;
