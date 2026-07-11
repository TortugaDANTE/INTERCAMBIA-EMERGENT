import { Ionicons } from "@expo/vector-icons";
import Constants from "expo-constants";
import * as Linking from "expo-linking";
import * as SecureStore from "expo-secure-store";
import * as ImagePicker from "expo-image-picker";
import * as Haptics from "expo-haptics";
import { LinearGradient } from "expo-linear-gradient";
import * as WebBrowser from "expo-web-browser";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ActivityIndicator,
  Keyboard,
  KeyboardAvoidingView,
  LayoutAnimation,
  Platform,
  Pressable,
  Image,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import Animated, { FadeInDown, FadeInUp } from "react-native-reanimated";
import { SafeAreaView, useSafeAreaInsets } from "react-native-safe-area-context";

const colors = {
  surface: "#F7FAF4",
  card: "#FFFFFF",
  ink: "#24212A",
  muted: "#7B7288",
  soft: "#E6E6E6",
  line: "#D1D5DB",
  brand: "#6B46C1",
  brandSoft: "#EFEAFB",
  green: "#48BB78",
  greenSoft: "#E6F7EE",
  terracotta: "#48BB78",
  dark: "#30283D",
};

const imageGradients = {
  camera: ["#6B46C1", "#30283D"],
  books: ["#48BB78", "#206A43"],
  plants: ["#7EE2A7", "#2D8A58"],
  bike: ["#8B5CF6", "#4C1D95"],
  laptop: ["#A78BFA", "#3B2A66"],
  box: ["#6B46C1", "#48BB78"],
};

const iconForImage = {
  camera: "camera-outline",
  books: "library-outline",
  plants: "leaf-outline",
  bike: "bicycle-outline",
  laptop: "laptop-outline",
  box: "cube-outline",
};

const API_BASE =
  Constants.expoConfig?.extra?.EXPO_PUBLIC_BACKEND_URL ||
  process.env.EXPO_PUBLIC_BACKEND_URL ||
  "";

const categories = ["Todo", "Productos", "Servicios", "Oficios", "Eco-hogar", "Perfil local"];
const TOKEN_KEY = "intercambia-session-token";

const categoryMatches = {
  Todo: () => true,
  Productos: (item) => item.kind === "producto",
  Servicios: (item) => item.kind === "servicio",
  Oficios: (item) => item.category === "Oficios",
  "Eco-hogar": (item) => ["Hogar", "Movilidad"].includes(item.category),
  "Perfil local": (item) => ["Tecnología", "Herramientas"].includes(item.category),
};

export default function Index() {
  const insets = useSafeAreaInsets();
  const [activeTab, setActiveTab] = useState("inicio");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [authUser, setAuthUser] = useState(null);
  const [authToken, setAuthToken] = useState("");
  const [authLoading, setAuthLoading] = useState(true);
  const [homeSection, setHomeSection] = useState("feed");

  const authHeaders = useMemo(() => (authToken ? { Authorization: `Bearer ${authToken}` } : {}), [authToken]);

  const saveToken = async (token) => {
    if (Platform.OS === "web") window.localStorage.setItem(TOKEN_KEY, token);
    else await SecureStore.setItemAsync(TOKEN_KEY, token);
  };

  const clearToken = async () => {
    if (Platform.OS === "web") window.localStorage.removeItem(TOKEN_KEY);
    else await SecureStore.deleteItemAsync(TOKEN_KEY);
  };

  const readToken = async () => (Platform.OS === "web" ? window.localStorage.getItem(TOKEN_KEY) || "" : await SecureStore.getItemAsync(TOKEN_KEY));

  const processAuthUrl = useCallback(async (url) => {
    const hash = url.includes("#") ? url.split("#")[1] : "";
    const query = url.includes("?") ? url.split("?")[1].split("#")[0] : "";
    const params = new URLSearchParams(hash || query);
    const sessionId = params.get("session_id");
    if (!sessionId) return false;
    const response = await fetch(`${API_BASE}/api/auth/google-session`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId }),
    });
    if (!response.ok) throw new Error("No se pudo iniciar sesión con Google");
    const user = await response.json();
    await saveToken(user.session_token);
    setAuthToken(user.session_token);
    setAuthUser(user);
    if (Platform.OS === "web") window.history.replaceState(null, "", window.location.pathname);
    showNotice("Sesión iniciada con Google.");
    return true;
  }, []);

  const checkAuth = useCallback(async () => {
    try {
      setAuthLoading(true);
      if (Platform.OS === "web") {
        const url = window.location.href;
        if (url.includes("session_id=")) {
          const handled = await processAuthUrl(url);
          if (handled) return;
        }
      }
      const token = await readToken();
      if (!token) return;
      const response = await fetch(`${API_BASE}/api/auth/me`, { headers: { Authorization: `Bearer ${token}` } });
      if (!response.ok) {
        await clearToken();
        return;
      }
      const user = await response.json();
      setAuthToken(token);
      setAuthUser(user);
    } catch {
      await clearToken();
    } finally {
      setAuthLoading(false);
    }
  }, [processAuthUrl]);

  const loginWithGoogle = useCallback(async () => {
    try {
      const redirectUrl = Platform.OS === "web" ? `${window.location.origin}/` : Linking.createURL("auth");
      const authUrl = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
      if (Platform.OS === "web") {
        window.location.href = authUrl;
        return;
      }
      const result = await WebBrowser.openAuthSessionAsync(authUrl, redirectUrl);
      if (result.type === "success" && result.url) await processAuthUrl(result.url);
    } catch (err) {
      showNotice(err && err.message ? err.message : "No se pudo abrir Google");
    }
  }, [processAuthUrl]);

  const loadData = useCallback(async (tokenOverride) => {
    try {
      setError("");
      setLoading(true);
      const token = typeof tokenOverride === "string" ? tokenOverride : authToken;
      const response = await fetch(`${API_BASE}/api/bootstrap`, { headers: token ? { Authorization: `Bearer ${token}` } : {} });
      if (!response.ok) throw new Error("No se pudo cargar Intercambia");
      const json = await response.json();
      setData(json);
    } catch (err) {
      setError(err && err.message ? err.message : "Error inesperado");
    } finally {
      setLoading(false);
    }
  }, [authToken]);

  const logout = useCallback(async () => {
    try {
      if (authToken) await fetch(`${API_BASE}/api/auth/logout`, { method: "POST", headers: authHeaders });
      await clearToken();
      setAuthToken("");
      setAuthUser(null);
      showNotice("Sesión cerrada.");
      loadData("");
    } catch {
      showNotice("No se pudo cerrar sesión.");
    }
  }, [authToken, authHeaders, loadData]);

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  useEffect(() => {
    loadData();
  }, [loadData, authToken]);

  useEffect(() => {
    if (!notice) return;
    const timeout = setTimeout(() => setNotice(""), 2500);
    return () => clearTimeout(timeout);
  }, [notice]);

  const switchTab = (tab) => {
    LayoutAnimation.configureNext(LayoutAnimation.Presets.easeInEaseOut);
    Haptics.selectionAsync();
    setActiveTab(tab);
  };

  const showNotice = (message) => {
    Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
    setNotice(message);
  };

  const content = useMemo(() => {
    if (loading) return <LoadingState />;
    if (error || !data) return <ErrorState message={error} onRetry={loadData} />;

    if (activeTab === "inicio") return <HomeFeed data={data} authUser={authUser} authLoading={authLoading} onLogin={loginWithGoogle} onLogout={logout} onInterest={showNotice} authHeaders={authHeaders} section={homeSection} onSectionChange={setHomeSection} />;
    if (activeTab === "mapa") return <MapDiscover points={data.barter_points} chains={data.trade_chains} plans={data.plans} authHeaders={authHeaders} onNotice={showNotice} />;
    if (activeTab === "bodega") return <BodegaProfile profile={data.profile} offers={data.offers} wishes={data.wishes} businesses={data.businesses || []} authUser={authUser} authHeaders={authHeaders} onLogin={loginWithGoogle} onCreated={loadData} onNotice={showNotice} />;
    if (activeTab === "crear") return <AddItemForm onCreated={loadData} onNotice={showNotice} authHeaders={authHeaders} />;
    return <ChatsScreen chats={data.chats} authHeaders={authHeaders} onNotice={showNotice} />;
  }, [activeTab, data, error, loadData, loading, authUser, authLoading, authHeaders, homeSection, loginWithGoogle, logout]);

  return (
    <SafeAreaView style={styles.safe} edges={["top", "bottom"]}>
      <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : "height"} style={styles.flex}>
        <View style={styles.appShell} testID="intercambia-app-shell">
          <AppHeader activeTab={activeTab} authUser={authUser} onLogin={loginWithGoogle} />
          <View style={styles.content}>{content}</View>
          {!!notice && <Toast message={notice} bottom={92 + insets.bottom} />}
          <BottomTabs activeTab={activeTab} onChange={switchTab} bottomInset={insets.bottom} />
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

function AppHeader({ activeTab, authUser, onLogin }) {
  const titleMap = {
    inicio: "Intercambia",
    mapa: "Puntos de trueque",
    bodega: "Mi bodega",
    crear: "Nueva publicación",
    chats: "Charlas",
  };

  return (
    <View style={styles.header} testID="sticky-app-header">
      <View>
        <Text style={styles.eyebrow}>Economía circular local</Text>
        <Text style={styles.headerTitle}>{titleMap[activeTab]}</Text>
      </View>
      <TouchableOpacity style={styles.headerIcon} testID="profile-shortcut-button" onPress={authUser ? () => Haptics.selectionAsync() : onLogin}>
        <Ionicons name={authUser ? "person-circle-outline" : "logo-google"} size={28} color={colors.brand} />
      </TouchableOpacity>
    </View>
  );
}

function LoadingState() {
  return (
    <View style={styles.centerState} testID="loading-state">
      <ActivityIndicator color={colors.brand} size="large" />
      <Text style={styles.stateText}>Cargando trueques...</Text>
    </View>
  );
}

function ErrorState({ message, onRetry }) {
  return (
    <View style={styles.centerState} testID="error-state">
      <Ionicons name="alert-circle-outline" size={42} color={colors.terracotta} />
      <Text style={styles.stateTitle}>Algo no cargó bien</Text>
      <Text style={styles.stateText}>{message}</Text>
      <TouchableOpacity style={styles.primaryButton} onPress={onRetry} testID="retry-load-button">
        <Text style={styles.primaryButtonText}>Reintentar</Text>
      </TouchableOpacity>
    </View>
  );
}

function HomeFeed({ data, authUser, authLoading, onLogin, onLogout, onInterest, authHeaders, section, onSectionChange }) {
  const [selectedCategory, setSelectedCategory] = useState("Todo");
  const [search, setSearch] = useState("");
  const filtered = data.feed.filter((item) => {
    const q = search.trim().toLowerCase();
    const matchesCategory = (categoryMatches[selectedCategory] || categoryMatches.Todo)(item);
    const haystack = `${item.title} ${item.description} ${item.category} ${(item.tags || []).join(" ")}`.toLowerCase();
    return matchesCategory && (!q || haystack.includes(q));
  });

  return (
    <View style={styles.flex} testID="home-feed-screen">
      <CategoryRow selected={selectedCategory} onSelect={setSelectedCategory} />
      <View style={styles.searchBar} testID="home-search-bar">
        <Ionicons name="search-outline" size={18} color={colors.muted} />
        <TextInput value={search} onChangeText={setSearch} placeholder="Buscar por producto, servicio o tag" placeholderTextColor="#9A9A91" style={styles.searchInput} testID="home-search-input" />
      </View>
      <ScrollView style={styles.scroll} contentContainerStyle={styles.feedContent} showsVerticalScrollIndicator={false}>
        <AuthProfileCard authUser={authUser} authLoading={authLoading} profile={data.profile} onLogin={onLogin} onLogout={onLogout} />
        <HomeSectionTabs section={section} onSectionChange={onSectionChange} />
        {section === "friends" && <FriendsPanel friends={data.friends || []} authHeaders={authHeaders} onNotice={onInterest} />}
        {section === "history" && <HistoryPanel history={data.trade_history || []} profile={data.profile} />}
        {section === "impact" && <ImpactPanel history={data.trade_history || []} profile={data.profile} />}
        {section !== "feed" ? null : <>
        <Animated.View entering={FadeInUp.delay(80)} style={styles.heroCard}>
          <View style={styles.heroCopy}>
            <Text style={styles.heroLabel}>intercambia</Text>
            <Text style={styles.heroTitle}>Convierte lo que tienes en lo que necesitas</Text>
            <Text style={styles.heroText}>Ofertas, deseos, servicios y puntos seguros en una sola comunidad.</Text>
          </View>
          <View style={styles.heroBubble}>
            <Ionicons name="sync-circle-outline" size={54} color={colors.brand} />
          </View>
        </Animated.View>

        <StatsRow profile={data.profile} />
        {data.profile.trial_active && <TrialBanner profile={data.profile} />}
        <AdCard point={data.barter_points?.[0]} />
        {!!(data.suggested_matches || []).length && <SuggestedMatches matches={data.suggested_matches} />}
        <Text style={styles.sectionTitle}>Actividad del muro</Text>
        {filtered.map((item, index) => <ItemCard key={item.id} item={item} index={index} onInterest={onInterest} authHeaders={authHeaders} />)}
        </>}
      </ScrollView>
    </View>
  );
}

function HomeSectionTabs({ section, onSectionChange }) {
  const tabs = [
    ["feed", "Inicio"],
    ["friends", "Amigos"],
    ["history", "Trueques"],
    ["impact", "Impacto"],
  ];
  return <View style={styles.homeTabs}>{tabs.map(([key, label]) => (
    <TouchableOpacity key={key} testID={`home-section-${key}-button`} style={[styles.homeTabButton, section === key && styles.homeTabActive]} onPress={() => onSectionChange(key)}>
      <Text style={[styles.homeTabText, section === key && styles.homeTabTextActive]}>{label}</Text>
    </TouchableOpacity>
  ))}</View>;
}

function FriendsPanel({ friends, authHeaders, onNotice }) {
  const act = async (friend, action) => {
    try {
      await fetch(`${API_BASE}/api/friends/${friend.id}/action?action=${action}`, { method: "POST", headers: authHeaders });
      onNotice(`${action} aplicado a ${friend.name}.`);
    } catch {
      onNotice("No se pudo actualizar amigo.");
    }
  };
  return <View style={styles.panelCard} testID="friends-panel"><Text style={styles.sectionTitle}>Mis amigos</Text>{friends.map((friend) => (
    <View key={friend.id} style={styles.friendRow}>
      <View style={styles.avatarCircle}><Ionicons name="person" size={18} color={colors.brand} /></View>
      <View style={styles.friendCopy}><Text style={styles.friendName}>{friend.name}</Text><Text style={styles.friendMeta}>{friend.handle} · {friend.city} · {friend.status}</Text></View>
      <TouchableOpacity testID={`friend-add-${friend.id}`} onPress={() => act(friend, "agregar")}><Ionicons name="person-add-outline" size={20} color={colors.green} /></TouchableOpacity>
      <TouchableOpacity testID={`friend-block-${friend.id}`} onPress={() => act(friend, "bloquear")}><Ionicons name="ban-outline" size={20} color={colors.brand} /></TouchableOpacity>
      <TouchableOpacity testID={`friend-report-${friend.id}`} onPress={() => act(friend, "reportar")}><Ionicons name="flag-outline" size={20} color="#B42318" /></TouchableOpacity>
    </View>
  ))}</View>;
}

function HistoryPanel({ history, profile }) {
  return <View style={styles.panelCard} testID="history-panel"><Text style={styles.sectionTitle}>Historial de trueques</Text>{history.map((trade) => (
    <View key={trade.id} style={styles.historyRow}><Text style={styles.friendName}>{trade.title}</Text><Text style={styles.friendMeta}>Diste: {trade.gave} (${trade.gave_value})</Text><Text style={styles.friendMeta}>Recibiste: {trade.received} (${trade.received_value})</Text><Text style={[styles.friendMeta, { color: trade.result_value >= 0 ? colors.green : "#B42318" }]}>Resultado: {trade.result_value >= 0 ? "+" : ""}${trade.result_value} MXN</Text></View>
  ))}<Text style={styles.impactTotal}>Impacto total: {profile.circular_impact}</Text></View>;
}

function ImpactPanel({ history, profile }) {
  const positive = history.filter((trade) => trade.result_value >= 0).reduce((sum, trade) => sum + trade.result_value, 0);
  const negative = history.filter((trade) => trade.result_value < 0).reduce((sum, trade) => sum + Math.abs(trade.result_value), 0);
  return <View style={styles.panelCard} testID="impact-panel"><Text style={styles.sectionTitle}>Impacto económico</Text><Text style={styles.impactBig}>{profile.circular_impact}</Text><Text style={styles.bodyText}>Ganancia acumulada: ${positive.toLocaleString("es-MX")} MXN</Text><Text style={styles.bodyText}>Valor cedido o pérdida: ${negative.toLocaleString("es-MX")} MXN</Text><Text style={styles.bodyText}>Este cálculo compara el valor de lo que diste contra lo que recibiste en trueques completados.</Text></View>;
}

function SuggestedMatches({ matches }) {
  return <View style={styles.panelCard} testID="suggested-matches-section"><Text style={styles.sectionTitle}>Intercambios sugeridos</Text>{matches.map((match) => (
    <View key={match.id} style={styles.matchRow}><Ionicons name="git-compare-outline" size={22} color={colors.brand} /><View style={styles.friendCopy}><Text style={styles.friendName}>{match.source_title} ↔ {match.matched_title}</Text><Text style={styles.friendMeta}>{match.matched_owner} · {match.reason}</Text><Text style={[styles.friendMeta, { color: match.value_delta >= 0 ? colors.green : colors.muted }]}>Diferencia estimada: {match.value_delta >= 0 ? "+" : ""}${match.value_delta.toLocaleString("es-MX")}</Text></View></View>
  ))}</View>;
}

function AuthProfileCard({ authUser, authLoading, profile, onLogin, onLogout }) {
  return (
    <View style={styles.authCard} testID="auth-profile-card">
      <View style={styles.profileMiniAvatar}>
        <Text style={styles.profileMiniInitial}>{(authUser?.name || profile.name || "I").charAt(0).toUpperCase()}</Text>
      </View>
      <View style={styles.authCopy}>
        <Text style={styles.authTitle}>{authUser ? authUser.name : "Entra a tu perfil"}</Text>
        <Text style={styles.authText}>{authUser ? `${authUser.email} · ${authUser.plan_label}${authUser.trial_active ? ` · ${authUser.trial_days_left} días gratis` : ""}` : "Usa Google y activa 7 días gratis con todas las funciones."}</Text>
      </View>
      <TouchableOpacity disabled={authLoading} style={styles.authButton} testID={authUser ? "logout-button" : "google-login-button"} onPress={authUser ? onLogout : onLogin}>
        <Ionicons name={authUser ? "log-out-outline" : "logo-google"} size={18} color="#fff" />
      </TouchableOpacity>
    </View>
  );
}

function TrialBanner({ profile }) {
  return (
    <View style={styles.trialBanner} testID="trial-banner-card">
      <View style={styles.trialIcon}>
        <Ionicons name="sparkles-outline" size={22} color="#fff" />
      </View>
      <View style={styles.trialCopy}>
        <Text style={styles.trialTitle}>Prueba completa activa</Text>
        <Text style={styles.trialText}>Tienes {profile.trial_days_left} días para usar Premium y Cruce de datos sin límites.</Text>
      </View>
    </View>
  );
}

function CategoryRow({ selected, onSelect }) {
  return (
    <View style={styles.chipBar} testID="category-filter-row">
      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.chipBarContent}>
        {categories.map((category) => {
          const isSelected = selected === category;
          return (
            <TouchableOpacity key={category} testID={`category-chip-${category.toLowerCase()}`} style={[styles.categoryChip, isSelected && styles.categoryChipSelected]} onPress={() => onSelect(category)}>
              <Text style={[styles.categoryChipText, isSelected && styles.categoryChipTextSelected]}>{category}</Text>
            </TouchableOpacity>
          );
        })}
      </ScrollView>
    </View>
  );
}

function StatsRow({ profile }) {
  return (
    <View style={styles.statsRow} testID="impact-stats-row">
      <StatCard label="Amigos" value={`${profile.friends}`} />
      <StatCard label="Trueques" value={`${profile.completed_trades}`} />
      <StatCard label="Impacto" value={profile.circular_impact.split(" ")[0]} />
    </View>
  );
}

function StatCard({ label, value }) {
  return (
    <View style={styles.statCard}>
      <Text style={styles.statValue}>{value}</Text>
      <Text style={styles.statLabel}>{label}</Text>
    </View>
  );
}

function AdCard({ point }) {
  return (
    <View style={styles.adCard} testID="sponsored-ad-card">
      <View style={styles.adIcon}>
        <Ionicons name="megaphone-outline" size={20} color={colors.brand} />
      </View>
      <View style={styles.adCopy}>
        <Text style={styles.adLabel}>Punto de trueque cercano</Text>
        <Text style={styles.adText}>{point ? `${point.name}: ${point.perks}` : "Negocios locales pueden promover sus puntos de trueque aquí."}</Text>
      </View>
    </View>
  );
}

function ItemCard({ item, index, onInterest, authHeaders }) {
  const gradient = imageGradients[item.image_key] || imageGradients.box;
  const icon = iconForImage[item.image_key] || "cube-outline";

  const registerInterest = async () => {
    if (item.requires_premium_contact) {
      onInterest("Premium requerido para contactar trueques mayores a $2,000 MXN.");
      return;
    }
    try {
      await fetch(`${API_BASE}/api/interests`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeaders },
        body: JSON.stringify({ item_id: item.id, message: `Me interesa ${item.title}` }),
      });
      onInterest("Interés enviado. Revisa tus charlas.");
    } catch {
      onInterest("Guardamos tu intención localmente.");
    }
  };

  return (
    <Animated.View entering={FadeInDown.delay(index * 70)} style={styles.itemCard} testID={`feed-item-card-${item.id}`}>
      <View style={styles.ownerRow}>
        <View style={styles.avatarCircle}><Ionicons name="person" size={18} color={colors.brand} /></View>
        <View style={styles.ownerText}>
          <Text style={styles.ownerName}>{item.owner_name}</Text>
          <Text style={styles.ownerMeta}>{item.location} · {item.kind}</Text>
        </View>
        <View style={[styles.typePill, item.listing_type === "deseo" && styles.wishPill]}>
          <Text style={[styles.typePillText, item.listing_type === "deseo" && styles.wishPillText]}>{item.listing_type === "oferta" ? "Ofrece" : "Busca"}</Text>
        </View>
      </View>

      <LinearGradient colors={gradient} style={styles.itemImage}>
        {item.images?.[0] ? <Image source={{ uri: item.images[0] }} style={styles.uploadedItemImage} /> : <Ionicons name={icon} size={70} color="rgba(255,255,255,0.92)" />}
        {item.requires_premium_contact && <View style={styles.premiumOverlay}><Ionicons name="lock-closed-outline" size={26} color="#fff" /><Text style={styles.premiumOverlayText}>Detalles Premium</Text></View>}
        <LinearGradient colors={["transparent", "rgba(42,42,42,0.76)"]} style={styles.imageScrim}>
          <Text style={styles.imageTitle}>{item.title}</Text>
          <Text style={styles.imageValue}>${item.estimated_value.toLocaleString("es-MX")} {item.currency}</Text>
        </LinearGradient>
      </LinearGradient>

      <Text style={styles.itemDescription}>{item.description}</Text>
      <View style={styles.exchangeBox}>
        <Ionicons name="repeat-outline" size={18} color={colors.terracotta} />
        <Text style={styles.exchangeText}>Acepta: {item.exchange_for}</Text>
      </View>
      {!!item.tags?.length && <View style={styles.tagWrap}>{item.tags.slice(0, 5).map((tag) => <Text key={tag} style={styles.tagChip}>#{tag}</Text>)}</View>}

      <View style={styles.actionRow}>
        <TouchableOpacity style={styles.secondaryButton} onPress={registerInterest} testID={`interest-button-${item.id}`}>
          <Ionicons name="heart-outline" size={18} color={colors.brand} />
          <Text style={styles.secondaryButtonText}>{item.requires_premium_contact ? "Premium" : "Me interesa"}</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.commentButton} onPress={() => onInterest("Comentario preparado para la charla.")} testID={`comment-button-${item.id}`}>
          <Ionicons name="chatbubble-outline" size={18} color={colors.muted} />
          <Text style={styles.commentText}>{item.comments}</Text>
        </TouchableOpacity>
      </View>
    </Animated.View>
  );
}

function MapDiscover({ points, chains, plans, authHeaders, onNotice }) {
  const [selectedPoint, setSelectedPoint] = useState(points[0]);

  return (
    <ScrollView style={styles.scroll} contentContainerStyle={styles.mapContent} showsVerticalScrollIndicator={false} testID="map-discover-screen">
      <View style={styles.searchGlass}>
        <Ionicons name="search-outline" size={18} color={colors.muted} />
        <Text style={styles.searchText}>Buscar cafeterías, talleres o plazas</Text>
      </View>
      <LinearGradient colors={["#EFEAFB", "#E6F7EE"]} style={styles.mapCanvas}>
        <View style={[styles.mapRoad, styles.mapRoadOne]} />
        <View style={[styles.mapRoad, styles.mapRoadTwo]} />
        {points.map((point, index) => (
          <TouchableOpacity key={point.id} testID={`barter-point-pin-${point.id}`} style={[styles.mapPin, { left: `${22 + index * 25}%`, top: `${28 + (index % 2) * 30}%` }]} onPress={() => { Haptics.selectionAsync(); setSelectedPoint(point); }}>
            <Ionicons name="location" size={24} color={colors.terracotta} />
          </TouchableOpacity>
        ))}
        <View style={styles.mapLegend}>
          <Text style={styles.mapLegendTitle}>Mapa de trueques</Text>
          <Text style={styles.mapLegendText}>Vista inicial por zonas, lista para crecer con ubicación real.</Text>
        </View>
      </LinearGradient>

      <View style={styles.pointSheet} testID="barter-point-detail-sheet">
        <View style={styles.sheetHandle} />
        <Text style={styles.sheetLabel}>Punto premium</Text>
        <Text style={styles.sheetTitle}>{selectedPoint.name}</Text>
        <Text style={styles.sheetSubtitle}>{selectedPoint.business_type} · {selectedPoint.zone}</Text>
        <Text style={styles.sheetAddress}>{selectedPoint.address}</Text>
        <Text style={styles.bodyText}>{selectedPoint.perks}</Text>
        <View style={styles.acceptsWrap}>
          {selectedPoint.accepts.map((accept) => <View key={accept} style={styles.smallChip}><Text style={styles.smallChipText}>{accept}</Text></View>)}
        </View>
      </View>

      <View style={styles.chainCard} testID="business-point-onboarding-card">
        <View style={styles.chainHeader}>
          <Ionicons name="storefront-outline" size={22} color={colors.brand} />
          <Text style={styles.chainTitle}>Registra tu negocio como punto seguro</Text>
        </View>
        <Text style={styles.bodyText}>Cafés, talleres y locales pueden crear su página, ofrecer electricidad para probar aparatos, publicar promos y aceptar trueque parcial.</Text>
        <Text style={styles.chainStep}>Flujo: 1) Crear página de negocio en Bodega  2) Validar datos  3) Suscribirse a Premium Puntos de Trueque.</Text>
      </View>

      <Text style={styles.sectionTitle}>Cadenas premium sugeridas</Text>
      <PremiumPlans plans={plans || []} authHeaders={authHeaders} onNotice={onNotice} />
      {chains.map((chain) => (
        <View key={chain.id} style={styles.chainCard} testID={`trade-chain-card-${chain.id}`}>
          <View style={styles.chainHeader}>
            <Ionicons name="git-network-outline" size={22} color={colors.brand} />
            <Text style={styles.chainTitle}>{chain.title}</Text>
          </View>
          {chain.steps.map((step, index) => <Text key={`${chain.id}-${step}`} style={styles.chainStep}>{index + 1}. {step}</Text>)}
          <View style={styles.chainFooter}>
            <Text style={styles.chainMetric}>{chain.estimated_gain}</Text>
            <Text style={styles.chainMetric}>{chain.distance}</Text>
          </View>
        </View>
      ))}
    </ScrollView>
  );
}

function PremiumPlans({ plans, authHeaders, onNotice }) {
  const subscribe = async (tier) => {
    try {
      const response = await fetch(`${API_BASE}/api/billing/create-checkout-session`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeaders },
        body: JSON.stringify({ tier, return_url: Platform.OS === "web" ? window.location.origin : "frontend://" }),
      });
      if (response.status === 401) throw new Error("Inicia sesión para suscribirte.");
      if (!response.ok) throw new Error("El checkout de pago aún no está configurado.");
      const data = await response.json();
      await WebBrowser.openBrowserAsync(data.url);
    } catch (err) {
      onNotice(err && err.message ? err.message : "No se pudo abrir la suscripción.");
    }
  };

  return (
    <View style={styles.planWrap} testID="premium-plans-section">
      {plans.map((plan) => (
        <View key={plan.tier} style={styles.planCard}>
          <Text style={styles.planTitle}>{plan.label}</Text>
          <Text style={styles.planPrice}>{plan.monthly_label}</Text>
          {plan.features.map((feature) => <Text key={feature} style={styles.planFeature}>• {feature}</Text>)}
          <TouchableOpacity style={styles.planButton} testID={`subscribe-${plan.tier}-button`} onPress={() => subscribe(plan.tier)}>
            <Text style={styles.planButtonText}>{plan.tier === "business" ? "Registrar y validar pago" : "Suscribirme"}</Text>
          </TouchableOpacity>
        </View>
      ))}
    </View>
  );
}

function BodegaProfile({ profile, offers, wishes, businesses, authUser, authHeaders, onLogin, onCreated, onNotice }) {
  const [mode, setMode] = useState("bodega");
  const list = mode === "bodega" ? offers : wishes;

  return (
    <View style={styles.flex} testID="bodega-profile-screen">
      <View style={styles.segmentWrap}>
        <TouchableOpacity testID="bodega-segment-button" style={[styles.segmentButton, mode === "bodega" && styles.segmentActive]} onPress={() => setMode("bodega")}>
          <Text style={[styles.segmentText, mode === "bodega" && styles.segmentTextActive]}>Bodega</Text>
        </TouchableOpacity>
        <TouchableOpacity testID="wishes-segment-button" style={[styles.segmentButton, mode === "deseos" && styles.segmentActive]} onPress={() => setMode("deseos")}>
          <Text style={[styles.segmentText, mode === "deseos" && styles.segmentTextActive]}>Deseos</Text>
        </TouchableOpacity>
      </View>
      <ScrollView style={styles.scroll} contentContainerStyle={styles.profileContent} showsVerticalScrollIndicator={false}>
        <View style={styles.profileCard}>
          <View style={styles.profileAvatar}><Ionicons name="person" size={34} color={colors.brand} /></View>
          <Text style={styles.profileName}>{profile.name}</Text>
          <Text style={styles.profileHandle}>{profile.handle} · {profile.city}</Text>
          <Text style={styles.profileBio}>{profile.bio}</Text>
          <View style={styles.planPill}><Text style={styles.planPillText}>{profile.trial_active ? `Prueba completa · ${profile.trial_days_left} días restantes` : `${profile.plan_label} · límite gratis $${profile.free_value_limit.toLocaleString("es-MX")} MXN`}</Text></View>
          <StatsRow profile={profile} />
        </View>
        <BusinessSection businesses={businesses} authUser={authUser} authHeaders={authHeaders} onLogin={onLogin} onCreated={onCreated} onNotice={onNotice} />
        {list.length === 0 ? (
          <View style={styles.emptyShelf} testID="empty-bodega-state">
            <Ionicons name="file-tray-outline" size={42} color={colors.muted} />
            <Text style={styles.stateTitle}>Tu bodega está vacía</Text>
            <Text style={styles.stateText}>Agrega lo que ofreces o lo que necesitas para cruzar datos.</Text>
          </View>
        ) : list.map((item, index) => <InventoryRow key={item.id} item={item} index={index} authHeaders={authHeaders} onChanged={onCreated} onNotice={onNotice} />)}
      </ScrollView>
    </View>
  );
}

function BusinessSection({ businesses, authUser, authHeaders, onLogin, onCreated, onNotice }) {
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [category, setCategory] = useState("Cafetería");
  const [address, setAddress] = useState("");
  const [description, setDescription] = useState("");
  const [profileType, setProfileType] = useState("persona_moral");
  const [saving, setSaving] = useState(false);
  const [expandedBusinessId, setExpandedBusinessId] = useState("");
  const [businessPost, setBusinessPost] = useState({ title: "", description: "", listing_type: "oferta", kind: "producto", category: "General", estimated_value: "", exchange_for: "" });

  const submitBusiness = async () => {
    if (!authUser) {
      onLogin();
      return;
    }
    if (!name.trim() || !address.trim() || !description.trim()) {
      onNotice("Completa nombre, dirección y descripción de la tienda.");
      return;
    }
    try {
      setSaving(true);
      const response = await fetch(`${API_BASE}/api/businesses`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeaders },
        body: JSON.stringify({ name, category, address, description, profile_type: profileType }),
      });
      if (!response.ok) {
        const payload = await response.json();
        throw new Error(payload.detail || "No se pudo registrar la tienda");
      }
      setName(""); setAddress(""); setDescription(""); setProfileType("persona_moral"); setShowForm(false);
      onNotice("Tienda de trueque registrada.");
      onCreated();
    } catch (err) {
      onNotice(err && err.message ? err.message : "No se pudo registrar.");
    } finally {
      setSaving(false);
    }
  };

  const submitBusinessPost = async (businessId) => {
    if (!businessPost.title.trim() || !businessPost.description.trim() || !businessPost.exchange_for.trim()) {
      onNotice("Completa título, descripción y qué busca/ofrece la tienda.");
      return;
    }
    try {
      const response = await fetch(`${API_BASE}/api/businesses/${businessId}/items`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeaders },
        body: JSON.stringify({
          title: businessPost.title,
          description: businessPost.description,
          listing_type: businessPost.listing_type,
          kind: businessPost.kind,
          category: businessPost.category,
          estimated_value: Number(businessPost.estimated_value || 0),
          exchange_for: businessPost.exchange_for,
          condition: businessPost.kind === "servicio" ? "Servicio" : "Nuevo o usado",
          pricing_model: businessPost.kind === "servicio" ? "por hora o a destajo" : "valor estimado",
          image_key: "box",
        }),
      });
      if (!response.ok) {
        const payload = await response.json();
        throw new Error(payload.detail || "No se pudo publicar en la tienda");
      }
      setBusinessPost({ title: "", description: "", listing_type: "oferta", kind: "producto", category: "General", estimated_value: "", exchange_for: "" });
      onNotice("Publicación agregada al sub perfil de negocio.");
      onCreated();
    } catch (err) {
      onNotice(err && err.message ? err.message : "No se pudo publicar.");
    }
  };

  const updateBusinessPost = (key, value) => setBusinessPost((current) => ({ ...current, [key]: value }));

  return (
    <View style={styles.businessCard} testID="business-pages-section">
      <View style={styles.businessHeader}>
        <View>
          <Text style={styles.businessTitle}>Mis tiendas de trueque</Text>
          <Text style={styles.businessText}>Gratis: 1 negocio. Premium: registros ilimitados.</Text>
        </View>
        <TouchableOpacity style={styles.businessAddButton} testID="add-business-button" onPress={() => authUser ? setShowForm(!showForm) : onLogin()}>
          <Ionicons name="storefront-outline" size={20} color="#fff" />
        </TouchableOpacity>
      </View>
      {businesses.map((business) => (
        <View key={business.id} style={styles.businessPageCard} testID={`business-row-${business.id}`}>
          <View style={styles.businessRow}>
            <View style={styles.businessLogo}><Ionicons name="business-outline" size={22} color={colors.brand} /></View>
            <View style={styles.businessRowCopy}>
              <Text style={styles.businessRowTitle}>{business.name}</Text>
              <Text style={styles.businessRowMeta}>{business.public_handle || "@tienda_trueque"} · {business.profile_type === "persona_fisica" ? "Persona física" : "Persona moral"}</Text>
              <Text style={styles.businessRowDesc}>{business.category} · {business.address}</Text>
              <Text style={styles.businessRowDesc}>{business.description}</Text>
            </View>
            <TouchableOpacity style={styles.inventoryMenuButton} testID={`business-expand-button-${business.id}`} onPress={() => setExpandedBusinessId(expandedBusinessId === business.id ? "" : business.id)}>
              <Ionicons name={expandedBusinessId === business.id ? "chevron-up" : "chevron-down"} size={18} color={colors.brand} />
            </TouchableOpacity>
          </View>
          <View style={styles.businessStatsRow}>
            <Text style={styles.businessStat}>{business.items?.filter((item) => item.listing_type === "oferta").length || 0} ofertas</Text>
            <Text style={styles.businessStat}>{business.items?.filter((item) => item.listing_type === "deseo").length || 0} necesidades</Text>
          </View>
          {expandedBusinessId === business.id && (
            <View style={styles.businessSubProfile} testID={`business-subprofile-${business.id}`}>
              <Text style={styles.businessSubTitle}>Publicaciones de la página</Text>
              {(business.items || []).length === 0 ? <Text style={styles.businessText}>Esta tienda aún no publica necesidades u ofertas.</Text> : business.items.map((item) => (
                <View key={item.id} style={styles.businessItemMini}>
                  <Text style={styles.businessItemTitle}>{item.listing_type === "oferta" ? "Ofrece" : "Necesita"}: {item.title}</Text>
                  <Text style={styles.businessItemMeta}>{item.category} · ${item.estimated_value.toLocaleString("es-MX")} · {item.status}</Text>
                </View>
              ))}
              <Text style={styles.businessSubTitle}>Publicar como {business.name}</Text>
              <View style={styles.optionRow}>
                <OptionButton label="Ofrece" selected={businessPost.listing_type === "oferta"} onPress={() => updateBusinessPost("listing_type", "oferta")} testID={`business-offer-type-${business.id}`} />
                <OptionButton label="Necesita" selected={businessPost.listing_type === "deseo"} onPress={() => updateBusinessPost("listing_type", "deseo")} testID={`business-need-type-${business.id}`} />
              </View>
              <LabeledInput label="Título" value={businessPost.title} onChangeText={(value) => updateBusinessPost("title", value)} placeholder="Ej. Café molido para trueque" testID={`business-post-title-${business.id}`} />
              <LabeledInput label="Descripción" value={businessPost.description} onChangeText={(value) => updateBusinessPost("description", value)} placeholder="Qué entra o qué necesita la tienda" multiline testID={`business-post-description-${business.id}`} />
              <LabeledInput label="Categoría" value={businessPost.category} onChangeText={(value) => updateBusinessPost("category", value)} placeholder="Alimentos, servicios, insumos..." testID={`business-post-category-${business.id}`} />
              <LabeledInput label="Valor estimado" value={businessPost.estimated_value} onChangeText={(value) => updateBusinessPost("estimated_value", value)} placeholder="500" keyboardType="numeric" testID={`business-post-value-${business.id}`} />
              <LabeledInput label="Qué acepta o busca" value={businessPost.exchange_for} onChangeText={(value) => updateBusinessPost("exchange_for", value)} placeholder="Insumos, servicios, productos locales..." multiline testID={`business-post-exchange-${business.id}`} />
              <TouchableOpacity style={styles.primaryButton} onPress={() => submitBusinessPost(business.id)} testID={`business-post-submit-${business.id}`}>
                <Text style={styles.primaryButtonText}>Publicar como página</Text>
              </TouchableOpacity>
            </View>
          )}
        </View>
      ))}
      {showForm && (
        <View style={styles.businessForm}>
          <LabeledInput label="Nombre del negocio" value={name} onChangeText={setName} placeholder="Café Semilla" testID="business-name-input" />
          <View style={styles.inputGroup} testID="business-page-type-section">
            <Text style={styles.inputLabel}>Tipo de página</Text>
            <View style={styles.optionRow}>
              <TouchableOpacity testID="business-legal-entity-button" style={[styles.optionButton, profileType === "persona_moral" && styles.optionButtonSelected]} onPress={() => setProfileType("persona_moral")}>
                <Text style={[styles.optionButtonText, profileType === "persona_moral" && styles.optionButtonTextSelected]}>Persona moral</Text>
              </TouchableOpacity>
              <TouchableOpacity testID="business-person-button" style={[styles.optionButton, profileType === "persona_fisica" && styles.optionButtonSelected]} onPress={() => setProfileType("persona_fisica")}>
                <Text style={[styles.optionButtonText, profileType === "persona_fisica" && styles.optionButtonTextSelected]}>Persona física</Text>
              </TouchableOpacity>
            </View>
          </View>
          <LabeledInput label="Categoría" value={category} onChangeText={setCategory} placeholder="Cafetería, taller, plaza..." testID="business-category-input" />
          <LabeledInput label="Dirección" value={address} onChangeText={setAddress} placeholder="Calle y colonia" testID="business-address-input" />
          <LabeledInput label="Descripción" value={description} onChangeText={setDescription} placeholder="Qué intercambios acepta" multiline testID="business-description-input" />
          <TouchableOpacity disabled={saving} style={styles.primaryButton} onPress={submitBusiness} testID="business-submit-button">
            {saving ? <ActivityIndicator color="#fff" /> : <Text style={styles.primaryButtonText}>Registrar tienda</Text>}
          </TouchableOpacity>
        </View>
      )}
    </View>
  );
}

function InventoryRow({ item, index, authHeaders, onChanged, onNotice }) {
  const icon = iconForImage[item.image_key] || "cube-outline";
  const [expanded, setExpanded] = useState(false);

  const updateStatus = async (status) => {
    try {
      const response = await fetch(`${API_BASE}/api/items/${item.id}/status`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json", ...authHeaders },
        body: JSON.stringify({ status }),
      });
      if (!response.ok) {
        const payload = await response.json();
        throw new Error(payload.detail || "No se pudo actualizar");
      }
      onNotice(status === "activo" ? "Publicación reactivada." : `Publicación marcada como ${status}.`);
      onChanged();
    } catch (err) {
      onNotice(err && err.message ? err.message : "No se pudo actualizar.");
    }
  };

  const deleteItem = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/items/${item.id}`, { method: "DELETE", headers: authHeaders });
      if (!response.ok) {
        const payload = await response.json();
        throw new Error(payload.detail || "No se pudo eliminar");
      }
      onNotice("Publicación eliminada de tu bodega.");
      onChanged();
    } catch (err) {
      onNotice(err && err.message ? err.message : "No se pudo eliminar.");
    }
  };

  return (
    <Animated.View entering={FadeInDown.delay(index * 65)} style={styles.inventoryRow} testID={`inventory-row-${item.id}`}>
      <View style={styles.inventoryIcon}><Ionicons name={icon} size={24} color={colors.brand} /></View>
      <View style={styles.inventoryCopy}>
        <View style={styles.inventoryTitleRow}>
          <Text style={styles.inventoryTitle}>{item.title}</Text>
          <TouchableOpacity style={styles.inventoryMenuButton} testID={`item-actions-button-${item.id}`} onPress={() => setExpanded(!expanded)}>
            <Ionicons name="ellipsis-horizontal" size={18} color={colors.brand} />
          </TouchableOpacity>
        </View>
        <Text style={styles.inventoryMeta}>{item.category} · {item.condition} · ${item.estimated_value.toLocaleString("es-MX")} · {item.status}</Text>
        <Text style={styles.inventoryTrade}>Por: {item.exchange_for}</Text>
        {expanded && (
          <View style={styles.itemActionsPanel} testID={`item-actions-panel-${item.id}`}>
            <ActionChip label="Activo" icon="play-outline" onPress={() => updateStatus("activo")} testID={`item-active-button-${item.id}`} />
            <ActionChip label="Pausar" icon="pause-outline" onPress={() => updateStatus("pausado")} testID={`item-pause-button-${item.id}`} />
            <ActionChip label="Vendido" icon="cash-outline" onPress={() => updateStatus("vendido")} testID={`item-sold-button-${item.id}`} />
            <ActionChip label="Truequeado" icon="swap-horizontal-outline" onPress={() => updateStatus("truequeado")} testID={`item-traded-button-${item.id}`} />
            <ActionChip label="Eliminar" icon="trash-outline" danger onPress={deleteItem} testID={`item-delete-button-${item.id}`} />
          </View>
        )}
      </View>
    </Animated.View>
  );
}

function ActionChip({ label, icon, onPress, testID, danger }) {
  return (
    <TouchableOpacity style={[styles.actionChip, danger && styles.actionChipDanger]} onPress={onPress} testID={testID}>
      <Ionicons name={icon} size={15} color={danger ? "#B42318" : colors.brand} />
      <Text style={[styles.actionChipText, danger && styles.actionChipTextDanger]}>{label}</Text>
    </TouchableOpacity>
  );
}

function AddItemForm({ onCreated, onNotice, authHeaders }) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState("General");
  const [kind, setKind] = useState("producto");
  const [listingType, setListingType] = useState("oferta");
  const [value, setValue] = useState("");
  const [exchangeFor, setExchangeFor] = useState("");
  const [tagsText, setTagsText] = useState("");
  const [images, setImages] = useState([]);
  const [saving, setSaving] = useState(false);
  const [validation, setValidation] = useState("");

  const pickImage = async () => {
    const current = await ImagePicker.getMediaLibraryPermissionsAsync();
    let permission = current;
    if (!current.granted && current.canAskAgain) permission = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!permission.granted) {
      setValidation("Permite acceso a fotos para subir imagen del producto.");
      return;
    }
    const result = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ["images"], allowsEditing: true, quality: 0.45, base64: true });
    if (!result.canceled && result.assets?.[0]?.base64) setImages([`data:image/jpeg;base64,${result.assets[0].base64}`]);
  };

  const submit = async () => {
    Keyboard.dismiss();
    const tags = tagsText.split(",").map((tag) => tag.trim().toLowerCase()).filter(Boolean).slice(0, 5);
    if (!title.trim() || !description.trim()) {
      setValidation("Completa título y descripción.");
      return;
    }
    if (tags.length < 3) {
      setValidation("Agrega entre 3 y 5 etiquetas separadas por coma.");
      return;
    }
    try {
      setSaving(true);
      setValidation("");
      const response = await fetch(`${API_BASE}/api/items`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeaders },
        body: JSON.stringify({ title, description, category, kind, listing_type: listingType, estimated_value: Number(value || 0), exchange_for: exchangeFor, condition: kind === "servicio" ? "Servicio" : "Usado", pricing_model: kind === "servicio" ? "por hora o a destajo" : "valor estimado", location: "Mi zona", image_key: "box", images, tags }),
      });
      if (!response.ok) {
        const payload = await response.json();
        throw new Error(payload.detail || "No se pudo publicar");
      }
      setTitle("");
      setDescription("");
      setExchangeFor("");
      setValue("");
      setTagsText("");
      setImages([]);
      onNotice("Publicación agregada a tu bodega.");
      onCreated();
    } catch (err) {
      setValidation(err && err.message ? err.message : "Error al guardar");
    } finally {
      setSaving(false);
    }
  };

  return (
    <View style={styles.formShell} testID="add-item-form-screen">
      <ScrollView style={styles.scroll} contentContainerStyle={styles.formContent} keyboardShouldPersistTaps="handled" showsVerticalScrollIndicator={false}>
        <Text style={styles.formIntro}>Formulario flexible para productos, servicios, oficios y necesidades.</Text>
        <TouchableOpacity style={styles.imagePickerBox} onPress={pickImage} testID="item-image-picker-button">
          {images[0] ? <Image source={{ uri: images[0] }} style={styles.formPreviewImage} /> : <><Ionicons name="image-outline" size={30} color={colors.brand} /><Text style={styles.imagePickerText}>Subir imagen del producto</Text></>}
        </TouchableOpacity>
        <LabeledInput label="Título" value={title} onChangeText={setTitle} placeholder="Ej. Reparación de bicicleta" testID="item-title-input" />
        <LabeledInput label="Descripción" value={description} onChangeText={setDescription} placeholder="Estado, detalles, alcance del servicio..." multiline testID="item-description-input" />
        <Text style={styles.inputLabel}>Tipo de publicación</Text>
        <View style={styles.optionRow}>
          <OptionButton label="Ofrezco" selected={listingType === "oferta"} onPress={() => setListingType("oferta")} testID="offer-type-button" />
          <OptionButton label="Busco" selected={listingType === "deseo"} onPress={() => setListingType("deseo")} testID="wish-type-button" />
        </View>
        <Text style={styles.inputLabel}>Clase</Text>
        <View style={styles.optionRow}>
          <OptionButton label="Producto" selected={kind === "producto"} onPress={() => setKind("producto")} testID="product-kind-button" />
          <OptionButton label="Servicio" selected={kind === "servicio"} onPress={() => setKind("servicio")} testID="service-kind-button" />
        </View>
        <LabeledInput label="Categoría flexible" value={category} onChangeText={setCategory} placeholder="Oficios, salud, arte, hogar..." testID="item-category-input" />
        <LabeledInput label="Valor estimado en moneda local" value={value} onChangeText={setValue} placeholder="1200" keyboardType="numeric" testID="item-value-input" />
        <LabeledInput label="Qué aceptas o buscas a cambio (opcional)" value={exchangeFor} onChangeText={setExchangeFor} placeholder="Opcional: herramientas, clases, dinero parcial..." multiline testID="item-exchange-input" />
        <LabeledInput label="Etiquetas del producto (3 a 5, separadas por coma)" value={tagsText} onChangeText={setTagsText} placeholder="bicicleta, movilidad, plegable" testID="item-tags-input" />
        {!!validation && <Text style={styles.validationText} testID="form-validation-text">{validation}</Text>}
      </ScrollView>
      <View style={styles.stickyAction}>
        <TouchableOpacity disabled={saving} style={[styles.primaryButton, saving && styles.disabledButton]} onPress={submit} testID="create-item-submit-button">
          {saving ? <ActivityIndicator color="#fff" /> : <Text style={styles.primaryButtonText}>Publicar en Intercambia</Text>}
        </TouchableOpacity>
      </View>
    </View>
  );
}

function LabeledInput({ label, testID, ...props }) {
  return (
    <View style={styles.inputGroup}>
      <Text style={styles.inputLabel}>{label}</Text>
      <TextInput {...props} testID={testID} placeholderTextColor="#9A9A91" style={[styles.input, props.multiline && styles.multilineInput]} />
    </View>
  );
}

function OptionButton({ label, selected, onPress, testID }) {
  return (
    <TouchableOpacity testID={testID} style={[styles.optionButton, selected && styles.optionButtonSelected]} onPress={onPress}>
      <Text style={[styles.optionButtonText, selected && styles.optionButtonTextSelected]}>{label}</Text>
    </TouchableOpacity>
  );
}

function ChatsScreen({ chats, authHeaders, onNotice }) {
  const [activeChat, setActiveChat] = useState(null);
  const [messages, setMessages] = useState([]);
  const [text, setText] = useState("");
  const messagesRef = useRef(null);

  const openChat = async (chat) => {
    setActiveChat(chat);
    try {
      const response = await fetch(`${API_BASE}/api/chats/${chat.id}/messages`);
      if (response.ok) setMessages(await response.json());
      setTimeout(() => messagesRef.current?.scrollToEnd?.({ animated: true }), 120);
    } catch {
      onNotice("No se pudieron cargar mensajes.");
    }
  };

  const sendMessage = async () => {
    if (!activeChat || !text.trim()) return;
    try {
      const response = await fetch(`${API_BASE}/api/chats/${activeChat.id}/messages`, { method: "POST", headers: { "Content-Type": "application/json", ...authHeaders }, body: JSON.stringify({ text }) });
      if (!response.ok) throw new Error("No se pudo enviar");
      const message = await response.json();
      setMessages((current) => [...current, message]);
      setText("");
      setTimeout(() => messagesRef.current?.scrollToEnd?.({ animated: true }), 120);
    } catch {
      onNotice("No se pudo enviar el mensaje.");
    }
  };

  if (activeChat) {
    return <View style={styles.chatDetail} testID="chat-detail-screen">
      <TouchableOpacity style={styles.backRow} onPress={() => setActiveChat(null)} testID="chat-back-button"><Ionicons name="chevron-back" size={20} color={colors.brand} /><Text style={styles.chatName}>{activeChat.with_user}</Text></TouchableOpacity>
      <ScrollView ref={messagesRef} style={styles.scroll} contentContainerStyle={styles.messagesContent}>{messages.map((message) => (
        <View key={message.id} style={[styles.messageBubble, message.sender_id === "demo-user" && styles.messageBubbleMine]}><Text style={styles.messageSender}>{message.sender_name}</Text><Text style={styles.messageText}>{message.text}</Text></View>
      ))}</ScrollView>
      <View style={styles.messageComposer}><TextInput value={text} onChangeText={setText} placeholder="Escribe un mensaje" placeholderTextColor="#9A9A91" style={styles.messageInput} testID="chat-message-input" /><TouchableOpacity style={styles.sendButton} onPress={sendMessage} testID="chat-send-button"><Ionicons name="send" size={18} color="#fff" /></TouchableOpacity></View>
    </View>;
  }

  return (
    <ScrollView style={styles.scroll} contentContainerStyle={styles.chatContent} showsVerticalScrollIndicator={false} testID="chats-screen">
      <Text style={styles.formIntro}>Conversaciones para acordar entregas, cadenas y puntos seguros.</Text>
      {chats.map((chat) => (
        <Pressable key={chat.id} style={styles.chatRow} testID={`chat-row-${chat.id}`} onPress={() => openChat(chat)}>
          <View style={styles.avatarCircleLarge}><Ionicons name="person" size={22} color={colors.brand} /></View>
          <View style={styles.chatCopy}>
            <View style={styles.chatTopLine}>
              <Text style={styles.chatName}>{chat.with_user}</Text>
              {chat.unread > 0 && <Text style={styles.unreadBadge}>{chat.unread}</Text>}
            </View>
            <Text style={styles.chatItem}>{chat.related_item}</Text>
            <Text style={styles.chatMessage}>{chat.last_message}</Text>
          </View>
        </Pressable>
      ))}
    </ScrollView>
  );
}

function BottomTabs({ activeTab, onChange, bottomInset }) {
  const tabs = [
    { key: "inicio", label: "Inicio", icon: "home-outline" },
    { key: "mapa", label: "Mapa", icon: "map-outline" },
    { key: "bodega", label: "Bodega", icon: "file-tray-stacked-outline" },
    { key: "crear", label: "Crear", icon: "add-circle-outline" },
    { key: "chats", label: "Chats", icon: "chatbubbles-outline" },
  ];

  return (
    <View style={[styles.tabBar, { paddingBottom: Math.max(bottomInset, 8) }]} testID="bottom-tab-bar">
      {tabs.map((tab) => {
        const active = activeTab === tab.key;
        return (
          <TouchableOpacity key={tab.key} testID={`tab-${tab.key}-button`} style={styles.tabButton} onPress={() => onChange(tab.key)}>
            <Ionicons name={tab.icon} size={23} color={active ? colors.brand : colors.muted} />
            <Text style={[styles.tabLabel, active && styles.tabLabelActive]}>{tab.label}</Text>
          </TouchableOpacity>
        );
      })}
    </View>
  );
}

function Toast({ message, bottom }) {
  return (
    <Animated.View entering={FadeInDown} style={[styles.toast, { bottom }]} testID="toast-message">
      <Ionicons name="checkmark-circle" size={18} color="#fff" />
      <Text style={styles.toastText}>{message}</Text>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.surface },
  flex: { flex: 1 },
  appShell: { flex: 1, backgroundColor: colors.surface, overflow: "hidden" },
  header: { minHeight: 82, paddingHorizontal: 20, paddingTop: 14, paddingBottom: 14, borderBottomWidth: 1, borderBottomColor: colors.line, flexDirection: "row", alignItems: "center", justifyContent: "space-between", backgroundColor: colors.card },
  eyebrow: { fontSize: 12, color: colors.green, fontWeight: "800", letterSpacing: 0.6, textTransform: "uppercase" },
  headerTitle: { fontSize: 30, fontWeight: "800", color: colors.ink, marginTop: 2 },
  headerIcon: { width: 48, height: 48, borderRadius: 16, backgroundColor: colors.brandSoft, alignItems: "center", justifyContent: "center", borderWidth: 1, borderColor: "#E1D6FA" },
  content: { flex: 1, paddingBottom: 78 },
  scroll: { flex: 1 },
  searchBar: { height: 52, marginHorizontal: 20, marginBottom: 6, borderRadius: 20, backgroundColor: colors.card, borderWidth: 1, borderColor: colors.line, paddingHorizontal: 14, flexDirection: "row", alignItems: "center", gap: 8 },
  searchInput: { flex: 1, color: colors.ink, fontSize: 15 },
  centerState: { flex: 1, alignItems: "center", justifyContent: "center", paddingHorizontal: 28, gap: 14 },
  stateTitle: { fontSize: 22, fontWeight: "800", color: colors.ink, textAlign: "center" },
  stateText: { fontSize: 15, color: colors.muted, textAlign: "center", lineHeight: 22 },
  chipBar: { height: 56, justifyContent: "center", backgroundColor: colors.surface },
  chipBarContent: { paddingHorizontal: 20, gap: 10, alignItems: "center" },
  categoryChip: { height: 36, flexShrink: 0, paddingHorizontal: 16, borderRadius: 18, borderWidth: 1, borderColor: colors.line, backgroundColor: colors.card, alignItems: "center", justifyContent: "center" },
  categoryChipSelected: { backgroundColor: colors.brand, borderColor: colors.brand },
  categoryChipText: { fontSize: 14, color: colors.muted, fontWeight: "600" },
  categoryChipTextSelected: { color: "#fff" },
  feedContent: { paddingHorizontal: 20, paddingBottom: 28, gap: 18 },
  homeTabs: { flexDirection: "row", gap: 8 },
  homeTabButton: { flex: 1, minHeight: 40, borderRadius: 20, backgroundColor: colors.card, borderWidth: 1, borderColor: colors.line, alignItems: "center", justifyContent: "center" },
  homeTabActive: { backgroundColor: colors.brand, borderColor: colors.brand },
  homeTabText: { color: colors.muted, fontSize: 12, fontWeight: "900" },
  homeTabTextActive: { color: "#fff" },
  panelCard: { backgroundColor: colors.card, borderRadius: 22, borderWidth: 1, borderColor: colors.line, padding: 16, gap: 12 },
  friendRow: { flexDirection: "row", alignItems: "center", gap: 10, paddingVertical: 8, borderBottomWidth: 1, borderBottomColor: colors.line },
  friendCopy: { flex: 1 },
  friendName: { color: colors.ink, fontSize: 15, fontWeight: "900" },
  friendMeta: { color: colors.muted, fontSize: 12, lineHeight: 18, marginTop: 2 },
  historyRow: { backgroundColor: colors.surface, borderRadius: 16, padding: 12, borderWidth: 1, borderColor: colors.line },
  impactTotal: { color: colors.brand, fontSize: 18, fontWeight: "900", marginTop: 4 },
  impactBig: { color: colors.green, fontSize: 28, fontWeight: "900" },
  matchRow: { flexDirection: "row", gap: 10, backgroundColor: colors.brandSoft, borderRadius: 16, padding: 12 },
  authCard: { backgroundColor: colors.card, borderRadius: 22, borderWidth: 1, borderColor: colors.line, padding: 14, flexDirection: "row", alignItems: "center", gap: 12 },
  profileMiniAvatar: { width: 48, height: 48, borderRadius: 16, backgroundColor: colors.brand, alignItems: "center", justifyContent: "center" },
  profileMiniInitial: { color: "#fff", fontSize: 20, fontWeight: "900" },
  authCopy: { flex: 1 },
  authTitle: { color: colors.ink, fontSize: 16, fontWeight: "900" },
  authText: { color: colors.muted, fontSize: 13, lineHeight: 18, marginTop: 3 },
  authButton: { width: 44, height: 44, borderRadius: 14, backgroundColor: colors.brand, alignItems: "center", justifyContent: "center" },
  trialBanner: { backgroundColor: colors.brand, borderRadius: 22, padding: 16, flexDirection: "row", alignItems: "center", gap: 12 },
  trialIcon: { width: 46, height: 46, borderRadius: 16, backgroundColor: colors.green, alignItems: "center", justifyContent: "center" },
  trialCopy: { flex: 1 },
  trialTitle: { color: "#fff", fontSize: 17, fontWeight: "900" },
  trialText: { color: "rgba(255,255,255,0.86)", fontSize: 13, lineHeight: 19, marginTop: 3 },
  heroCard: { borderRadius: 26, backgroundColor: colors.brandSoft, padding: 22, flexDirection: "row", overflow: "hidden", borderWidth: 1, borderColor: "#E1D6FA" },
  heroCopy: { flex: 1, paddingRight: 8 },
  heroLabel: { color: colors.brand, fontSize: 13, fontWeight: "900", marginBottom: 7, textTransform: "lowercase" },
  heroTitle: { color: colors.ink, fontSize: 24, lineHeight: 29, fontWeight: "900" },
  heroText: { color: colors.muted, fontSize: 15, lineHeight: 22, marginTop: 10 },
  heroBubble: { width: 84, height: 84, borderRadius: 42, backgroundColor: "rgba(255,255,255,0.65)", alignItems: "center", justifyContent: "center", alignSelf: "center" },
  statsRow: { flexDirection: "row", gap: 10, width: "100%" },
  statCard: { flex: 1, backgroundColor: colors.card, borderRadius: 18, paddingVertical: 16, alignItems: "center", borderWidth: 1, borderColor: colors.line },
  statValue: { fontSize: 21, fontWeight: "900", color: colors.green },
  statLabel: { fontSize: 12, color: colors.muted, marginTop: 4, fontWeight: "600" },
  sectionTitle: { fontSize: 22, fontWeight: "900", color: colors.ink, marginTop: 4 },
  itemCard: { backgroundColor: colors.card, borderRadius: 24, padding: 14, borderWidth: 1, borderColor: colors.line, shadowColor: "#000", shadowOpacity: 0.05, shadowRadius: 12, shadowOffset: { width: 0, height: 8 }, elevation: 2 },
  ownerRow: { flexDirection: "row", alignItems: "center", marginBottom: 12 },
  avatarCircle: { width: 36, height: 36, borderRadius: 18, backgroundColor: colors.brandSoft, alignItems: "center", justifyContent: "center" },
  ownerText: { flex: 1, marginLeft: 10 },
  ownerName: { fontSize: 15, fontWeight: "800", color: colors.ink },
  ownerMeta: { fontSize: 12, color: colors.muted, marginTop: 2 },
  typePill: { borderRadius: 999, backgroundColor: colors.brandSoft, paddingHorizontal: 12, paddingVertical: 7 },
  wishPill: { backgroundColor: colors.greenSoft },
  typePillText: { color: colors.brand, fontSize: 12, fontWeight: "800" },
  wishPillText: { color: colors.green },
  itemImage: { height: 202, borderRadius: 20, overflow: "hidden", alignItems: "center", justifyContent: "center" },
  uploadedItemImage: { width: "100%", height: "100%", resizeMode: "cover" },
  premiumOverlay: { position: "absolute", top: 14, right: 14, borderRadius: 18, backgroundColor: "rgba(107,70,193,0.88)", paddingHorizontal: 10, paddingVertical: 8, flexDirection: "row", gap: 6, alignItems: "center" },
  premiumOverlayText: { color: "#fff", fontSize: 12, fontWeight: "900" },
  imageScrim: { position: "absolute", left: 0, right: 0, bottom: 0, padding: 16, paddingTop: 52 },
  imageTitle: { color: "#fff", fontSize: 22, fontWeight: "900" },
  imageValue: { color: "rgba(255,255,255,0.86)", fontSize: 14, fontWeight: "700", marginTop: 4 },
  itemDescription: { color: colors.ink, fontSize: 15, lineHeight: 22, marginTop: 14 },
  exchangeBox: { flexDirection: "row", gap: 8, backgroundColor: colors.greenSoft, borderRadius: 16, padding: 12, marginTop: 12 },
  exchangeText: { flex: 1, fontSize: 14, color: colors.dark, lineHeight: 20 },
  tagWrap: { flexDirection: "row", flexWrap: "wrap", gap: 8, marginTop: 10 },
  tagChip: { color: colors.brand, backgroundColor: colors.brandSoft, borderRadius: 999, overflow: "hidden", paddingHorizontal: 10, paddingVertical: 6, fontSize: 12, fontWeight: "900" },
  actionRow: { flexDirection: "row", gap: 10, marginTop: 14 },
  primaryButton: { minHeight: 52, borderRadius: 26, backgroundColor: colors.brand, alignItems: "center", justifyContent: "center", paddingHorizontal: 20, flexDirection: "row" },
  primaryButtonText: { color: "#fff", fontSize: 16, fontWeight: "900" },
  disabledButton: { opacity: 0.7 },
  secondaryButton: { flex: 1, minHeight: 48, borderRadius: 24, backgroundColor: colors.brandSoft, alignItems: "center", justifyContent: "center", flexDirection: "row", gap: 8 },
  secondaryButtonText: { color: colors.brand, fontSize: 15, fontWeight: "800" },
  commentButton: { width: 76, minHeight: 48, borderRadius: 24, backgroundColor: colors.soft, alignItems: "center", justifyContent: "center", flexDirection: "row", gap: 6 },
  commentText: { color: colors.muted, fontWeight: "800" },
  mapContent: { paddingHorizontal: 20, paddingBottom: 28, gap: 18 },
  searchGlass: { height: 48, borderRadius: 24, backgroundColor: "rgba(255,255,255,0.78)", borderWidth: 1, borderColor: colors.line, paddingHorizontal: 16, flexDirection: "row", alignItems: "center", gap: 8 },
  searchText: { color: colors.muted, fontSize: 14, fontWeight: "600" },
  mapCanvas: { height: 340, borderRadius: 28, overflow: "hidden", borderWidth: 1, borderColor: colors.line },
  mapRoad: { position: "absolute", height: 12, borderRadius: 8, backgroundColor: "rgba(255,255,255,0.68)", transform: [{ rotate: "-24deg" }] },
  mapRoadOne: { width: 420, left: -40, top: 105 },
  mapRoadTwo: { width: 360, left: -20, top: 230, transform: [{ rotate: "21deg" }] },
  mapPin: { position: "absolute", width: 50, height: 50, borderRadius: 25, backgroundColor: "rgba(255,255,255,0.92)", alignItems: "center", justifyContent: "center", borderWidth: 1, borderColor: "#E1D6FA" },
  mapLegend: { position: "absolute", left: 18, right: 18, bottom: 18, backgroundColor: "rgba(255,255,255,0.86)", borderRadius: 20, padding: 16 },
  mapLegendTitle: { fontSize: 18, color: colors.ink, fontWeight: "900" },
  mapLegendText: { color: colors.muted, fontSize: 13, lineHeight: 19, marginTop: 4 },
  pointSheet: { backgroundColor: colors.card, borderRadius: 26, padding: 18, borderWidth: 1, borderColor: colors.line },
  sheetHandle: { width: 46, height: 5, borderRadius: 999, backgroundColor: colors.line, alignSelf: "center", marginBottom: 12 },
  sheetLabel: { color: colors.green, fontSize: 12, fontWeight: "900", textTransform: "uppercase" },
  sheetTitle: { color: colors.ink, fontSize: 24, fontWeight: "900", marginTop: 4 },
  sheetSubtitle: { color: colors.brand, fontSize: 14, fontWeight: "800", marginTop: 2 },
  sheetAddress: { color: colors.muted, fontSize: 14, marginTop: 8 },
  bodyText: { color: colors.ink, fontSize: 15, lineHeight: 22, marginTop: 12 },
  acceptsWrap: { flexDirection: "row", flexWrap: "wrap", gap: 8, marginTop: 14 },
  smallChip: { backgroundColor: colors.brandSoft, borderRadius: 999, paddingHorizontal: 12, paddingVertical: 7 },
  smallChipText: { color: colors.brand, fontWeight: "800", fontSize: 12 },
  chainCard: { backgroundColor: colors.card, borderRadius: 22, borderWidth: 1, borderColor: colors.line, padding: 16 },
  chainHeader: { flexDirection: "row", alignItems: "center", gap: 8, marginBottom: 10 },
  chainTitle: { flex: 1, color: colors.ink, fontSize: 17, fontWeight: "900" },
  chainStep: { color: colors.dark, fontSize: 14, lineHeight: 22, marginTop: 3 },
  chainFooter: { flexDirection: "row", flexWrap: "wrap", gap: 8, marginTop: 12 },
  chainMetric: { color: colors.green, backgroundColor: colors.greenSoft, borderRadius: 999, paddingHorizontal: 10, paddingVertical: 6, fontSize: 12, fontWeight: "800" },
  planWrap: { gap: 12 },
  planCard: { backgroundColor: colors.brandSoft, borderRadius: 22, borderWidth: 1, borderColor: "#E1D6FA", padding: 16 },
  planTitle: { color: colors.brand, fontSize: 18, fontWeight: "900" },
  planPrice: { color: colors.green, fontSize: 14, fontWeight: "900", marginTop: 4 },
  planFeature: { color: colors.dark, fontSize: 13, lineHeight: 19, marginTop: 5 },
  planButton: { marginTop: 12, height: 44, borderRadius: 22, backgroundColor: colors.brand, alignItems: "center", justifyContent: "center" },
  planButtonText: { color: "#fff", fontWeight: "900", fontSize: 14 },
  segmentWrap: { height: 56, flexDirection: "row", gap: 8, paddingHorizontal: 20, alignItems: "center", backgroundColor: colors.surface },
  segmentButton: { flex: 1, height: 40, borderRadius: 20, backgroundColor: colors.card, borderWidth: 1, borderColor: colors.line, alignItems: "center", justifyContent: "center" },
  segmentActive: { backgroundColor: colors.brand, borderColor: colors.brand },
  segmentText: { color: colors.muted, fontSize: 14, fontWeight: "800" },
  segmentTextActive: { color: "#fff" },
  profileContent: { paddingHorizontal: 20, paddingBottom: 28, gap: 14 },
  profileCard: { backgroundColor: colors.card, borderRadius: 26, borderWidth: 1, borderColor: colors.line, padding: 20, alignItems: "center", gap: 10 },
  profileAvatar: { width: 74, height: 74, borderRadius: 37, backgroundColor: colors.brandSoft, alignItems: "center", justifyContent: "center" },
  profileName: { color: colors.ink, fontSize: 24, fontWeight: "900" },
  profileHandle: { color: colors.brand, fontSize: 14, fontWeight: "800" },
  profileBio: { color: colors.muted, fontSize: 14, lineHeight: 21, textAlign: "center" },
  planPill: { backgroundColor: colors.greenSoft, borderRadius: 999, paddingHorizontal: 12, paddingVertical: 7 },
  planPillText: { color: colors.green, fontSize: 12, fontWeight: "900" },
  businessCard: { backgroundColor: colors.card, borderRadius: 24, borderWidth: 1, borderColor: colors.line, padding: 16, gap: 14 },
  businessHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", gap: 12 },
  businessTitle: { color: colors.ink, fontSize: 18, fontWeight: "900" },
  businessText: { color: colors.muted, fontSize: 13, lineHeight: 18, marginTop: 3 },
  businessAddButton: { width: 46, height: 46, borderRadius: 16, backgroundColor: colors.brand, alignItems: "center", justifyContent: "center" },
  businessPageCard: { backgroundColor: colors.brandSoft, borderRadius: 20, padding: 12, gap: 12 },
  businessRow: { flexDirection: "row", gap: 10, alignItems: "flex-start" },
  businessLogo: { width: 42, height: 42, borderRadius: 14, backgroundColor: "#fff", alignItems: "center", justifyContent: "center" },
  businessRowCopy: { flex: 1 },
  businessRowTitle: { color: colors.ink, fontSize: 15, fontWeight: "900" },
  businessRowMeta: { color: colors.brand, fontSize: 12, fontWeight: "800", marginTop: 3 },
  businessRowDesc: { color: colors.dark, fontSize: 13, lineHeight: 18, marginTop: 4 },
  businessStatsRow: { flexDirection: "row", gap: 8 },
  businessStat: { color: colors.green, backgroundColor: colors.greenSoft, borderRadius: 999, paddingHorizontal: 10, paddingVertical: 6, fontSize: 12, fontWeight: "900" },
  businessSubProfile: { backgroundColor: colors.card, borderRadius: 18, padding: 12, gap: 12, borderWidth: 1, borderColor: colors.line },
  businessSubTitle: { color: colors.ink, fontSize: 15, fontWeight: "900" },
  businessItemMini: { backgroundColor: colors.surface, borderRadius: 14, padding: 10, borderWidth: 1, borderColor: colors.line },
  businessItemTitle: { color: colors.ink, fontSize: 13, fontWeight: "900" },
  businessItemMeta: { color: colors.muted, fontSize: 12, marginTop: 3, fontWeight: "700" },
  businessForm: { gap: 12 },
  emptyShelf: { backgroundColor: colors.card, borderRadius: 24, borderWidth: 1, borderColor: colors.line, padding: 24, alignItems: "center", gap: 10 },
  inventoryRow: { backgroundColor: colors.card, borderRadius: 20, borderWidth: 1, borderColor: colors.line, padding: 14, flexDirection: "row", gap: 12 },
  inventoryIcon: { width: 52, height: 52, borderRadius: 18, backgroundColor: colors.brandSoft, alignItems: "center", justifyContent: "center" },
  inventoryCopy: { flex: 1 },
  inventoryTitleRow: { flexDirection: "row", alignItems: "center", gap: 8 },
  inventoryTitle: { color: colors.ink, fontSize: 16, fontWeight: "900" },
  inventoryMenuButton: { width: 34, height: 34, borderRadius: 17, backgroundColor: colors.brandSoft, alignItems: "center", justifyContent: "center" },
  inventoryMeta: { color: colors.muted, fontSize: 12, marginTop: 4, fontWeight: "600" },
  inventoryTrade: { color: colors.dark, fontSize: 13, lineHeight: 19, marginTop: 6 },
  itemActionsPanel: { flexDirection: "row", flexWrap: "wrap", gap: 8, marginTop: 12, paddingTop: 12, borderTopWidth: 1, borderTopColor: colors.line },
  actionChip: { minHeight: 36, borderRadius: 18, paddingHorizontal: 10, backgroundColor: colors.brandSoft, flexDirection: "row", alignItems: "center", gap: 5 },
  actionChipDanger: { backgroundColor: "#FEE4E2" },
  actionChipText: { color: colors.brand, fontSize: 12, fontWeight: "900" },
  actionChipTextDanger: { color: "#B42318" },
  formShell: { flex: 1 },
  formContent: { paddingHorizontal: 20, paddingBottom: 110, gap: 14 },
  formIntro: { color: colors.muted, fontSize: 15, lineHeight: 22, marginBottom: 2 },
  imagePickerBox: { minHeight: 136, borderRadius: 22, borderWidth: 1, borderColor: "#E1D6FA", borderStyle: "dashed", backgroundColor: colors.brandSoft, alignItems: "center", justifyContent: "center", gap: 8, overflow: "hidden" },
  imagePickerText: { color: colors.brand, fontSize: 14, fontWeight: "900" },
  formPreviewImage: { width: "100%", height: 180, resizeMode: "cover" },
  inputGroup: { gap: 8 },
  inputLabel: { color: colors.ink, fontSize: 14, fontWeight: "900" },
  input: { minHeight: 52, borderRadius: 18, borderWidth: 1, borderColor: colors.line, backgroundColor: colors.card, paddingHorizontal: 16, color: colors.ink, fontSize: 15 },
  multilineInput: { minHeight: 104, paddingTop: 14, textAlignVertical: "top" },
  optionRow: { flexDirection: "row", gap: 10 },
  optionButton: { flex: 1, height: 48, borderRadius: 24, backgroundColor: colors.card, borderWidth: 1, borderColor: colors.line, alignItems: "center", justifyContent: "center" },
  optionButtonSelected: { backgroundColor: colors.brandSoft, borderColor: colors.brand },
  optionButtonText: { color: colors.muted, fontWeight: "800" },
  optionButtonTextSelected: { color: colors.brand },
  validationText: { color: colors.brand, fontSize: 14, fontWeight: "700", lineHeight: 20 },
  adCard: { backgroundColor: colors.brandSoft, borderRadius: 20, borderWidth: 1, borderColor: "#E1D6FA", padding: 14, flexDirection: "row", gap: 12, alignItems: "center" },
  adIcon: { width: 42, height: 42, borderRadius: 21, backgroundColor: "#FFFFFF", alignItems: "center", justifyContent: "center" },
  adCopy: { flex: 1 },
  adLabel: { color: colors.brand, fontSize: 12, fontWeight: "900", textTransform: "uppercase" },
  adText: { color: colors.dark, fontSize: 14, lineHeight: 20, marginTop: 3 },
  stickyAction: { position: "absolute", left: 0, right: 0, bottom: 0, backgroundColor: colors.surface, paddingHorizontal: 20, paddingTop: 10, paddingBottom: 14, borderTopWidth: 1, borderTopColor: colors.line },
  chatContent: { paddingHorizontal: 20, paddingBottom: 28, gap: 14 },
  chatRow: { backgroundColor: colors.card, borderRadius: 22, borderWidth: 1, borderColor: colors.line, padding: 14, flexDirection: "row", gap: 12, minHeight: 92 },
  avatarCircleLarge: { width: 54, height: 54, borderRadius: 27, backgroundColor: colors.brandSoft, alignItems: "center", justifyContent: "center" },
  chatCopy: { flex: 1 },
  chatTopLine: { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  chatName: { color: colors.ink, fontSize: 16, fontWeight: "900" },
  unreadBadge: { minWidth: 22, height: 22, borderRadius: 11, overflow: "hidden", backgroundColor: colors.green, color: "#fff", textAlign: "center", fontSize: 12, fontWeight: "900", paddingTop: 3 },
  chatItem: { color: colors.brand, fontSize: 12, fontWeight: "800", marginTop: 4 },
  chatMessage: { color: colors.muted, fontSize: 14, lineHeight: 20, marginTop: 5 },
  chatDetail: { flex: 1, paddingHorizontal: 20, paddingBottom: 0 },
  backRow: { flexDirection: "row", alignItems: "center", gap: 6, minHeight: 48 },
  messagesContent: { paddingBottom: 16, gap: 10 },
  messageBubble: { alignSelf: "flex-start", maxWidth: "82%", backgroundColor: colors.card, borderRadius: 18, borderWidth: 1, borderColor: colors.line, padding: 12 },
  messageBubbleMine: { alignSelf: "flex-end", backgroundColor: colors.brandSoft },
  messageSender: { color: colors.brand, fontSize: 11, fontWeight: "900", marginBottom: 3 },
  messageText: { color: colors.ink, fontSize: 14, lineHeight: 20 },
  messageComposer: { flexDirection: "row", gap: 8, paddingVertical: 10, backgroundColor: colors.surface },
  messageInput: { flex: 1, minHeight: 46, borderRadius: 23, backgroundColor: colors.card, borderWidth: 1, borderColor: colors.line, paddingHorizontal: 14, color: colors.ink },
  sendButton: { width: 46, height: 46, borderRadius: 23, backgroundColor: colors.brand, alignItems: "center", justifyContent: "center" },
  tabBar: { position: "absolute", left: 0, right: 0, bottom: 0, minHeight: 76, paddingTop: 9, borderTopWidth: 1, borderTopColor: "rgba(229,229,223,0.9)", flexDirection: "row", backgroundColor: "rgba(250,250,248,0.86)" },
  tabButton: { flex: 1, minHeight: 54, alignItems: "center", justifyContent: "center", gap: 3 },
  tabLabel: { color: colors.muted, fontSize: 11, fontWeight: "800" },
  tabLabelActive: { color: colors.brand },
  toast: { position: "absolute", left: 20, right: 20, minHeight: 46, borderRadius: 23, backgroundColor: colors.dark, flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 8, paddingHorizontal: 16 },
  toastText: { color: "#fff", fontWeight: "800", fontSize: 14 },
});
