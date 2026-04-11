import { Platform } from 'react-native';
import Constants from 'expo-constants';

const isExpoGo = Constants.appOwnership === 'expo';
let notificationsApi = null;

export async function initNotifications() {
  if (isExpoGo) {
    return false;
  }

  try {
    if (!notificationsApi) {
      notificationsApi = await import('expo-notifications');
    }

    notificationsApi.setNotificationHandler({
      handleNotification: async () => ({
        shouldShowBanner: true,
        shouldShowList: true,
        shouldPlaySound: false,
        shouldSetBadge: false,
      }),
    });

    if (Platform.OS === 'android') {
      await notificationsApi.setNotificationChannelAsync('operations', {
        name: 'Operations Alerts',
        importance: notificationsApi.AndroidImportance.HIGH,
      });
    }

    await notificationsApi.requestPermissionsAsync();
    return true;
  } catch {
    return false;
  }
}

export async function scheduleLocalNotification(title, body) {
  if (isExpoGo || !notificationsApi) {
    return false;
  }

  try {
    await notificationsApi.scheduleNotificationAsync({
      content: {
        title,
        body,
        sound: false,
      },
      trigger: Platform.OS === 'android' ? { channelId: 'operations' } : null,
    });
    return true;
  } catch {
    return false;
  }
}

export function getNotificationSupportLabel() {
  return isExpoGo ? 'Expo Go mode: in-app alerts enabled' : 'Local push alerts enabled';
}
