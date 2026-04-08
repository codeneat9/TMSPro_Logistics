import { Alert, PermissionsAndroid, Platform } from 'react-native';
import messaging from '@react-native-firebase/messaging';
import { notificationsAPI } from './api';

export const requestPushPermissions = async () => {
  try {
    if (Platform.OS === 'android' && Platform.Version >= 33) {
      const granted = await PermissionsAndroid.request(
        PermissionsAndroid.PERMISSIONS.POST_NOTIFICATIONS,
        {
          title: 'Notification Permission',
          message: 'TMS needs permission to send trip alerts and reroute updates.',
          buttonPositive: 'Allow',
        }
      );
      if (granted !== PermissionsAndroid.RESULTS.GRANTED) {
        return false;
      }
    }

    const authStatus = await messaging().requestPermission();
    return authStatus > 0;
  } catch {
    return false;
  }
};

export const registerDeviceForPush = async () => {
  try {
    await messaging().registerDeviceForRemoteMessages();
    const token = await messaging().getToken();
    if (token) {
      await notificationsAPI.registerDeviceToken(token, Platform.OS);
    }
    return token;
  } catch {
    return null;
  }
};

export const initializePushNotifications = async (onForegroundMessage) => {
  const granted = await requestPushPermissions();
  if (!granted) {
    return () => {};
  }

  await registerDeviceForPush();

  const unsubscribeOnMessage = messaging().onMessage(async (remoteMessage) => {
    if (onForegroundMessage) {
      onForegroundMessage(remoteMessage);
    } else {
      Alert.alert(
        remoteMessage?.notification?.title || 'TMS Alert',
        remoteMessage?.notification?.body || 'New trip event received'
      );
    }
  });

  const unsubscribeTokenRefresh = messaging().onTokenRefresh(async (token) => {
    try {
      await notificationsAPI.registerDeviceToken(token, Platform.OS);
    } catch {
      // Ignore token refresh sync failures; next app session will retry.
    }
  });

  return () => {
    unsubscribeOnMessage();
    unsubscribeTokenRefresh();
  };
};
