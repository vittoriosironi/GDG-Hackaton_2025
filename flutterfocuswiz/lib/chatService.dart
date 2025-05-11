import 'dart:convert';
import 'package:http/http.dart' as http;

class ChatService {
  // Base URL for your local server

  // Constructor with default localhost URL
  ChatService();

  /// Sends a message to the server and returns the response message(s)
  ///
  /// [message] is the text to send to the server
  /// Returns a Future with a list of response messages
  static Future<String> sendMessage(String message) async {
    // Prepare the request body
    final body = jsonEncode({'content': message});

    // Make the POST request
    final response = await http.post(
      Uri.parse('http://localhost:8080/message'),
      headers: {'Content-Type': 'application/json'},
      body: body,
    );

    // Check for errors
    if (response.statusCode != 200) {
      throw Exception('Failed to send message: ${response.statusCode}');
    }

    // Parse the response
    final Map<String, dynamic> data = jsonDecode(response.body);

    // Handle single message response
    return data['response'];
  }

  /// Notifies the server that a new focus session has started
  ///
  /// [durationMinutes] is the planned duration of the session in minutes
  /// [topic] is an optional description of the session focus
  /// Returns a Future with the server's response or null if there was an error
  static Future<void> startSession() async {
    try {
      // Prepare the request body

      // Make the POST request
      final response = await http.post(
        Uri.parse('http://localhost:8080/start-session'),
        headers: {'Content-Type': 'application/json'},
        body: null,
      );

      // Check for errors
      if (response.statusCode != 200) {
        throw Exception('Failed to start session: ${response.statusCode}');
      }

      // Parse and return the response
    } catch (e) {
      // Handle any exceptions
      print('Error starting session: $e');
      return null;
    }
  }

  static Future<void> stopSession() async {
    try {
      // Prepare the request body

      // Make the POST request
      final response = await http.post(
        Uri.parse('http://localhost:8080/stop-session'),
        headers: {'Content-Type': 'application/json'},
        body: null,
      );

      // Check for errors
      if (response.statusCode != 200) {
        throw Exception('Failed to start session: ${response.statusCode}');
      }

      // Parse and return the response
    } catch (e) {
      // Handle any exceptions
      print('Error starting session: $e');
      return null;
    }
  }
}
