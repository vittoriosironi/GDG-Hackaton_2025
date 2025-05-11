import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/cupertino.dart';
import 'package:flutterfocuswiz/chatService.dart'; // Added for macOS style widgets

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'FocusWiz',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xff0078FF), // macOS blue
          brightness: Brightness.light,
        ),
        fontFamily: 'SF Pro Text', // macOS font
        appBarTheme: const AppBarTheme(elevation: 0, centerTitle: true),
        cardTheme: CardTheme(
          elevation: 0,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(10),
            side: BorderSide(color: Colors.grey.shade200),
          ),
        ),
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
  Timer? _timer;
  bool _isLoading = false; // Track loading state for network requests

  // Options for the time selector dropdown
  final List<int> _timeOptions = [5, 10, 15, 25, 30, 45, 60];

  @override
  void dispose() {
    _timer?.cancel();
    _messageController.dispose();
    super.dispose();
  }

  void _startSession() async {
    // Notify server about session start
    try {
      await ChatService.startSession();
      setState(() {
        _isSessionActive = true;
        _remainingSeconds = _selectedMinutes * 60;
      });

      // Start the timer
      _timer = Timer.periodic(const Duration(seconds: 1), (timer) {
        setState(() {
          if (_remainingSeconds > 0) {
            _remainingSeconds--;
          } else {
            _stopSession(completed: true);
          }
        });
      });
    } catch (e) {
      // Handle error
      setState(() {
        _messages.add(
          ChatMessage(
            text: "Failed to start session: ${e.toString()}",
            isUser: false,
          ),
        );
      });
    } finally {}
  }

  void _stopSession({bool completed = false}) async {
    _timer?.cancel();

    // Calculate actual duration
    final int actualDurationMinutes =
        (_selectedMinutes * 60 - _remainingSeconds) ~/ 60;

    try {
      // Notify server about session end
      await ChatService.stopSession();

      setState(() {
        _isSessionActive = false;
        _remainingSeconds = 0;

        // Add server responses to chat
      });
    } catch (e) {
      // Handle error
      setState(() {
        _messages.add(
          ChatMessage(
            text: "Failed to stop session: ${e.toString()}",
            isUser: false,
          ),
        );
        _isSessionActive = false;
        _remainingSeconds = 0;
      });
    } finally {}
  }

  void _sendMessage() async {
    final messageText = _messageController.text.trim();

    if (messageText.isNotEmpty) {
      // Clear the input field immediately for better UX
      _messageController.clear();

      // Add the user's message to the chat
      setState(() {
        _messages.add(ChatMessage(text: messageText, isUser: true));
        _isLoading = true;
      });

      try {
        // Send the message to the server
        final response = await ChatService.sendMessage(messageText);

        setState(() {
          // Add all responses from the server

          _messages.add(ChatMessage(text: response, isUser: false));
        });
      } catch (e) {
        // Handle error
        setState(() {
          _messages.add(
            ChatMessage(
              text: "Failed to send message: ${e.toString()}",
              isUser: false,
            ),
          );
        });
      } finally {
        setState(() {
          _isLoading = false;
        });
      }
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
      backgroundColor: const Color(
        0xFFF5F5F7,
      ), // Light gray background like macOS
      appBar: AppBar(
        title: Image.asset(
          'resources/logo.png', // Path to the logo
          height: 25, // Adjust height as needed
          fit: BoxFit.contain,
        ),
        backgroundColor: Colors.white,
        foregroundColor: Colors.black87,
        elevation: 0,
        toolbarHeight: 44, // macOS style toolbar height
      ),
      body: Row(
        children: [
          // Left panel - Focus Session Controls
          Expanded(
            flex: 5,
            child: Padding(
              padding: const EdgeInsets.all(20.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // Session timer display - macOS style card
                  Container(
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(10),
                      boxShadow: [
                        BoxShadow(
                          color: Colors.black.withOpacity(0.05),
                          blurRadius: 10,
                          offset: const Offset(0, 2),
                        ),
                      ],
                    ),
                    padding: const EdgeInsets.all(24.0),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.center,
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          'Focus Timer',
                          style: TextStyle(
                            fontSize: 16,
                            color: Colors.grey.shade700,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                        const SizedBox(height: 24),
                        Text(
                          _isSessionActive
                              ? _formatTime(_remainingSeconds)
                              : 'Ready',
                          style: const TextStyle(
                            fontSize: 56,
                            fontWeight: FontWeight.w300,
                          ),
                        ),
                        const SizedBox(height: 30),
                        CupertinoButton(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 24,
                            vertical: 8,
                          ),
                          color:
                              _isSessionActive
                                  ? Colors.red
                                  : const Color(0xff0078FF),
                          borderRadius: BorderRadius.circular(20),
                          onPressed:
                              _isSessionActive
                                  ? () => _stopSession(completed: false)
                                  : _startSession,
                          child:
                              _isLoading
                                  ? const CupertinoActivityIndicator(
                                    color: Colors.white,
                                  )
                                  : Text(
                                    _isSessionActive ? 'End' : 'Start',
                                    style: const TextStyle(
                                      fontSize: 16,
                                      color: Colors.white,
                                    ),
                                  ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 16),

                  // Session time selector - macOS style
                  Container(
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(10),
                      boxShadow: [
                        BoxShadow(
                          color: Colors.black.withOpacity(0.05),
                          blurRadius: 10,
                          offset: const Offset(0, 2),
                        ),
                      ],
                    ),
                    padding: const EdgeInsets.all(16.0),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          'Duration',
                          style: TextStyle(
                            fontSize: 14,
                            color: Colors.grey.shade700,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                        const SizedBox(height: 10),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8),
                          decoration: BoxDecoration(
                            color: const Color(0xFFF5F5F7),
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: DropdownButtonHideUnderline(
                            child: DropdownButton<int>(
                              value: _selectedMinutes,
                              isExpanded: true,
                              icon: const Icon(
                                Icons.keyboard_arrow_down,
                                size: 20,
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
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),

          // Right panel - Chat Interface - macOS style
          Expanded(
            flex: 5,
            child: Container(
              color: Colors.white,
              child: Column(
                children: [
                  // Chat header - macOS style
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 16.0,
                      vertical: 10.0,
                    ),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      border: Border(
                        bottom: BorderSide(
                          color: Colors.grey.shade200,
                          width: 1,
                        ),
                      ),
                    ),
                    child: Row(
                      children: [
                        Icon(
                          CupertinoIcons.bubble_left,
                          color: Colors.grey.shade700,
                          size: 18,
                        ),
                        const SizedBox(width: 8),
                        Text(
                          'Notes',
                          style: TextStyle(
                            fontSize: 14,
                            color: Colors.grey.shade700,
                            fontWeight: FontWeight.w500,
                          ),
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
                                'No notes yet',
                                style: TextStyle(
                                  color: Colors.grey.shade500,
                                  fontSize: 14,
                                ),
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

                  // Message input area - macOS style
                  Container(
                    padding: const EdgeInsets.all(12.0),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      border: Border(
                        top: BorderSide(color: Colors.grey.shade200, width: 1),
                      ),
                    ),
                    child: Row(
                      children: [
                        Expanded(
                          child: Container(
                            decoration: BoxDecoration(
                              color: const Color(0xFFF5F5F7),
                              borderRadius: BorderRadius.circular(18),
                            ),
                            child: TextField(
                              controller: _messageController,
                              decoration: const InputDecoration(
                                hintText: 'Type a note...',
                                border: InputBorder.none,
                                contentPadding: EdgeInsets.symmetric(
                                  horizontal: 16,
                                  vertical: 10,
                                ),
                                hintStyle: TextStyle(
                                  color: Color(0xFFAEAEB2),
                                  fontSize: 14,
                                ),
                              ),
                              style: const TextStyle(fontSize: 14),
                              minLines: 1,
                              maxLines: 5,
                              onSubmitted: (_) => _sendMessage(),
                            ),
                          ),
                        ),
                        const SizedBox(width: 8),
                        GestureDetector(
                          onTap: _isLoading ? null : _sendMessage,
                          child: Container(
                            padding: const EdgeInsets.all(8),
                            decoration: BoxDecoration(
                              color:
                                  _isLoading
                                      ? Colors.grey
                                      : const Color(0xff0078FF),
                              borderRadius: BorderRadius.circular(16),
                            ),
                            child:
                                _isLoading
                                    ? const SizedBox(
                                      width: 16,
                                      height: 16,
                                      child: CircularProgressIndicator(
                                        color: Colors.white,
                                        strokeWidth: 2,
                                      ),
                                    )
                                    : const Icon(
                                      CupertinoIcons.arrow_up,
                                      color: Colors.white,
                                      size: 16,
                                    ),
                          ),
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
        padding: const EdgeInsets.symmetric(horizontal: 14.0, vertical: 8.0),
        decoration: BoxDecoration(
          color:
              isUser
                  ? const Color(0xff0078FF) // macOS blue for user messages
                  : const Color(0xFFE9E9EB), // macOS gray for system messages
          borderRadius: BorderRadius.circular(16.0),
        ),
        constraints: BoxConstraints(
          maxWidth: MediaQuery.of(context).size.width * 0.7,
        ),
        child: Text(
          message,
          style: TextStyle(
            color: isUser ? Colors.white : Colors.black,
            fontSize: 14,
          ),
        ),
      ),
    );
  }
}
