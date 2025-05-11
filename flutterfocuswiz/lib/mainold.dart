import 'dart:async';

import 'package:flutter/material.dart';

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'FocusWiz',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.blue),
        useMaterial3: true,
      ),
      home: const FocusSessionTracker(),
    );
  }
}

class FocusSessionTracker extends StatefulWidget {
  const FocusSessionTracker({super.key});

  @override
  State<FocusSessionTracker> createState() => _FocusSessionTrackerState();
}

class _FocusSessionTrackerState extends State<FocusSessionTracker> {
  final TextEditingController _messageController = TextEditingController();
  final List<ChatMessage> _messages = [];
  bool _isSessionActive = false;
  int _selectedMinutes = 25;
  int _remainingSeconds = 0;
  Timer? _timer; // Add this timer variable

  // Options for the time selector dropdown
  final List<int> _timeOptions = [5, 10, 15, 25, 30, 45, 60];

  @override
  void dispose() {
    _timer?.cancel(); // Cancel timer when widget is disposed
    _messageController.dispose();
    super.dispose();
  }

  void _startSession() {
    setState(() {
      _isSessionActive = true;
      _remainingSeconds = _selectedMinutes * 60;

      // Create and start timer
      _timer = Timer.periodic(const Duration(seconds: 1), (timer) {
        setState(() {
          if (_remainingSeconds > 0) {
            _remainingSeconds--;
          } else {
            _stopSession();
            // Optionally alert user that session is complete
            _messages.add(
              ChatMessage(
                text: "Your focus session is complete!",
                isUser: false,
              ),
            );
          }
        });
      });
    });
  }

  void _stopSession() {
    _timer?.cancel(); // Cancel the timer
    setState(() {
      _isSessionActive = false;
      _remainingSeconds = 0;
    });
  }

  void _sendMessage() {
    if (_messageController.text.trim().isNotEmpty) {
      setState(() {
        _messages.add(ChatMessage(text: _messageController.text, isUser: true));
        _messageController.clear();
      });
    }
  }

  String _formatTime(int seconds) {
    int minutes = seconds ~/ 60;
    int remainingSeconds = seconds % 60;
    return '${minutes.toString().padLeft(2, '0')}:${remainingSeconds.toString().padLeft(2, '0')}';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Image.asset(
          'resources/logo.png', // Path to the logo
          height: 20, // Adjust height as needed
          fit: BoxFit.contain,
        ),
        backgroundColor: Theme.of(context).colorScheme.primary,
        foregroundColor: Theme.of(context).colorScheme.onPrimary,
      ),
      body: Row(
        children: [
          // Left panel - Focus Session Controls
          Expanded(
            flex: 5,
            child: Padding(
              padding: const EdgeInsets.all(16.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Session timer display
                  Card(
                    elevation: 4,
                    child: Padding(
                      padding: const EdgeInsets.all(20.0),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.center,
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text(
                            'Focus Session',
                            style: Theme.of(context).textTheme.headlineSmall,
                          ),
                          const SizedBox(height: 20),
                          Text(
                            _isSessionActive
                                ? _formatTime(_remainingSeconds)
                                : 'Ready to focus?',
                            style: Theme.of(context).textTheme.displayMedium,
                          ),
                          const SizedBox(height: 30),
                          ElevatedButton(
                            onPressed:
                                _isSessionActive ? _stopSession : _startSession,
                            style: ElevatedButton.styleFrom(
                              padding: const EdgeInsets.symmetric(
                                horizontal: 40,
                                vertical: 15,
                              ),
                              backgroundColor:
                                  _isSessionActive
                                      ? Colors.red
                                      : Theme.of(context).colorScheme.primary,
                              foregroundColor: Colors.white,
                            ),
                            child: Text(
                              _isSessionActive
                                  ? 'End Session'
                                  : 'Start Session',
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 20),

                  // Session time selector
                  Card(
                    elevation: 4,
                    child: Padding(
                      padding: const EdgeInsets.all(16.0),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text(
                            'Session Duration',
                            style: Theme.of(context).textTheme.titleMedium,
                          ),
                          const SizedBox(height: 10),
                          DropdownButtonFormField<int>(
                            value: _selectedMinutes,
                            decoration: const InputDecoration(
                              border: OutlineInputBorder(),
                              contentPadding: EdgeInsets.symmetric(
                                horizontal: 16,
                                vertical: 8,
                              ),
                            ),
                            items:
                                _timeOptions
                                    .map(
                                      (minutes) => DropdownMenuItem<int>(
                                        value: minutes,
                                        child: Text('$minutes minutes'),
                                      ),
                                    )
                                    .toList(),
                            onChanged:
                                _isSessionActive
                                    ? null
                                    : (value) {
                                      if (value != null) {
                                        setState(() {
                                          _selectedMinutes = value;
                                        });
                                      }
                                    },
                          ),
                        ],
                      ),
                    ),
                  ),

                  // Session history would go here
                  const SizedBox(height: 20),
                  Expanded(
                    child: Card(
                      elevation: 4,
                      child: Padding(
                        padding: const EdgeInsets.all(16.0),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'Session History',
                              style: Theme.of(context).textTheme.titleMedium,
                            ),
                            const SizedBox(height: 10),
                            const Expanded(
                              child: Center(
                                child: Text(
                                  'Your session history will appear here',
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),

          // Right panel - Chat Interface
          Expanded(
            flex: 5,
            child: Container(
              decoration: BoxDecoration(
                border: Border(
                  left: BorderSide(color: Colors.grey.shade300, width: 1),
                ),
              ),
              child: Column(
                children: [
                  // Chat header
                  Container(
                    padding: const EdgeInsets.all(16.0),
                    color: Colors.grey.shade100,
                    child: Row(
                      children: [
                        const Icon(Icons.chat_outlined),
                        const SizedBox(width: 8),
                        Text(
                          'Session Chat',
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                      ],
                    ),
                  ),

                  // Chat messages area
                  Expanded(
                    child:
                        _messages.isEmpty
                            ? Center(
                              child: Text(
                                'No messages yet. Start the conversation!',
                                style: TextStyle(color: Colors.grey.shade600),
                              ),
                            )
                            : ListView.builder(
                              padding: const EdgeInsets.all(16.0),
                              reverse: true,
                              itemCount: _messages.length,
                              itemBuilder: (context, index) {
                                final message =
                                    _messages[_messages.length - 1 - index];
                                return MessageBubble(
                                  message: message.text,
                                  isUser: message.isUser,
                                );
                              },
                            ),
                  ),

                  // Message input area
                  Container(
                    padding: const EdgeInsets.all(8.0),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      boxShadow: [
                        BoxShadow(
                          offset: const Offset(0, -2),
                          color: Colors.grey.shade200,
                          blurRadius: 4,
                        ),
                      ],
                    ),
                    child: Row(
                      children: [
                        Expanded(
                          child: TextField(
                            controller: _messageController,
                            decoration: const InputDecoration(
                              hintText: 'Type a message...',
                              border: OutlineInputBorder(),
                              contentPadding: EdgeInsets.all(12),
                            ),
                            minLines: 1,
                            maxLines: 5,
                            onSubmitted: (_) => _sendMessage(),
                          ),
                        ),
                        const SizedBox(width: 8),
                        IconButton(
                          icon: const Icon(Icons.send),
                          onPressed: _sendMessage,
                          color: Theme.of(context).colorScheme.primary,
                          iconSize: 28,
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class ChatMessage {
  final String text;
  final bool isUser;

  ChatMessage({required this.text, required this.isUser});
}

class MessageBubble extends StatelessWidget {
  final String message;
  final bool isUser;

  const MessageBubble({super.key, required this.message, required this.isUser});

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 4.0),
        padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 10.0),
        decoration: BoxDecoration(
          color:
              isUser
                  ? Theme.of(context).colorScheme.primary
                  : Colors.grey.shade200,
          borderRadius: BorderRadius.circular(20.0),
        ),
        constraints: BoxConstraints(
          maxWidth: MediaQuery.of(context).size.width * 0.7,
        ),
        child: Text(
          message,
          style: TextStyle(color: isUser ? Colors.white : Colors.black),
        ),
      ),
    );
  }
}
