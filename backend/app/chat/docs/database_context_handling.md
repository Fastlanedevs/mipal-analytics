# Database Context Handling in Conversations

This document outlines how the system handles database context in conversations, particularly when users switch between different databases during analytics sessions.

## Current Implementation

Each message in a conversation can include references to a specific database and table through the `database_uid` and `table_uid` fields. This context is maintained across the conversation and is used for executing analytics queries against the correct data source.

### How It Works

1. When a user initiates an analytics conversation with ANALYST_PAL or Analytics_pal, they typically specify a database to query
2. The system stores the `database_uid` and `table_uid` (if applicable) with each message
3. When the assistant responds, it inherits the database context from the parent message
4. **For database switches**: The current implementation creates a new conversation thread when a user switches databases
   - This ensures clean context separation
   - Prevents confusion about which database analyses refer to
   - Makes conversation history more meaningful and organized

### Technical Implementation

- The Neo4j schema for the `Message` node includes `database_uid` and `table_uid` as optional `StringProperty` fields
- The `ChatRepository.save_message` method ensures these fields are saved to the database
- The `_create_user_message` and `_store_assistant_message` methods in `ChatService` properly handle these fields
- The REST API includes these fields in the MessageDTO for frontend use

## Future Possibilities

While the current implementation (creating new conversation threads for database switches) provides a clean separation of concerns, here are additional approaches that could be considered in future updates:

### 1. Explicit Context Switch Acknowledgment
- System explicitly acknowledges database changes in responses
- Example: "I see you've switched from Sales database to Marketing database. Your previous analysis was about sales trends."
- Helps users understand the change in context

### 2. Conversation Segmenting
- Visually segment the conversation when database context changes
- Add a visual divider or header: "Now discussing Marketing Database (previously: Sales Database)"
- Helps users mentally organize the information flow

### 3. Context History Tracking
- Maintain a history of database contexts within the conversation metadata
- Allow users to see which database was active during each part of the conversation
- Could be shown as a timeline or color-coding of messages

### 4. Context-Aware Analysis
- When analyzing across database changes, acknowledge both contexts
- "Based on what we saw in the Sales database earlier, this pattern in the Marketing database suggests..."
- Enables cross-database insights

### 5. Offer Conversation Forking
- When a significant database change occurs, offer to create a new conversation
- "You've switched databases. Would you like to continue in this conversation or start a fresh one?"
- Gives users a choice between continued context or clean separation

### 6. Persistence of Important Insights
- When changing databases, summarize key insights from the previous database
- Store these summaries as part of the conversation history
- Helps preserve knowledge across context shifts

### 7. Database Connection in UI
- Visually indicate which database a message is referring to in the UI
- Could use badges/labels on messages: "Sales DB", "Marketing DB"
- Helps users quickly identify context

## Conclusion

The current approach of creating new conversation threads when databases change provides a clean and straightforward user experience that balances technical simplicity with usability. As the product evolves, we may consider implementing some of the additional options above based on user feedback and needs. 