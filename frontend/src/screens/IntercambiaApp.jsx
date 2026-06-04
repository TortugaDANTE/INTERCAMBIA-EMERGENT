import { Ionicons } from "@expo/vector-icons";
import Constants from "expo-constants";
import * as Haptics from "expo-haptics";
import { LinearGradient } from "expo-linear-gradient";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Keyboard,
  KeyboardAvoidingView,
  LayoutAnimation,
  Platform,
  Pressable,
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

  const loadData = useCallback(async () => {
    try {
      setError("");
      setLoading(true);
      const response = await fetch(`${API_BASE}/api/bootstrap`);
      if (!response.ok) throw new Error("No se pudo cargar Intercambia");
      const json = await response.json();
      setData(json);
    } catch (err) {
      setError(err && err.message ? err.message : "Error inesperado");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // Initial mobile data hydration is intentionally triggered once on mount.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadData();
  }, [loadData]);

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

    if (activeTab === "inicio") return <HomeFeed data={data} onInterest={showNotice} />;
    if (activeTab === "mapa") return <MapDiscover points={data.barter_points} chains={data.trade_chains} />;
    if (activeTab === "bodega") return <BodegaProfile profile={data.profile} offers={data.offers} wishes={data.wishes} />;
    if (activeTab === "crear") return <AddItemForm onCreated={loadData} onNotice={showNotice} />;
    return <ChatsScreen chats={data.chats} />;
  }, [activeTab, data, error, loadData, loading]);

  return (
    <SafeAreaView style={styles.safe} edges={["top", "bottom"]}>
      <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : "height"} style={styles.flex}>
        <View style={styles.appShell} testID="intercambia-app-shell">
          <AppHeader activeTab={activeTab} />
          <View style={styles.content}>{content}</View>
          {!!notice && <Toast message={notice} bottom={92 + insets.bottom} />}
          <BottomTabs activeTab={activeTab} onChange={switchTab} bottomInset={insets.bottom} />
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

function AppHeader({ activeTab }) {
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
      <TouchableOpacity style={styles.headerIcon} testID="profile-shortcut-button" onPress={() => Haptics.selectionAsync()}>
        <Ionicons name="person-circle-outline" size={28} color={colors.brand} />
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

function HomeFeed({ data, onInterest }) {
  const [selectedCategory, setSelectedCategory] = useState("Todo");
  const filtered = data.feed.filter((item) => (categoryMatches[selectedCategory] || categoryMatches.Todo)(item));

  return (
    <View style={styles.flex} testID="home-feed-screen">
      <CategoryRow selected={selectedCategory} onSelect={setSelectedCategory} />
      <ScrollView style={styles.scroll} contentContainerStyle={styles.feedContent} showsVerticalScrollIndicator={false}>
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
        <AdCard />
        <Text style={styles.sectionTitle}>Actividad del muro</Text>
        {filtered.map((item, index) => <ItemCard key={item.id} item={item} index={index} onInterest={onInterest} />)}
      </ScrollView>
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

function AdCard() {
  return (
    <View style={styles.adCard} testID="sponsored-ad-card">
      <View style={styles.adIcon}>
        <Ionicons name="megaphone-outline" size={20} color={colors.brand} />
      </View>
      <View style={styles.adCopy}>
        <Text style={styles.adLabel}>Espacio patrocinado</Text>
        <Text style={styles.adText}>Negocios locales pueden promover sus puntos de trueque aquí.</Text>
      </View>
    </View>
  );
}

function ItemCard({ item, index, onInterest }) {
  const gradient = imageGradients[item.image_key] || imageGradients.box;
  const icon = iconForImage[item.image_key] || "cube-outline";

  const registerInterest = async () => {
    try {
      await fetch(`${API_BASE}/api/interests`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
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
        <Ionicons name={icon} size={70} color="rgba(255,255,255,0.92)" />
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

      <View style={styles.actionRow}>
        <TouchableOpacity style={styles.secondaryButton} onPress={registerInterest} testID={`interest-button-${item.id}`}>
          <Ionicons name="heart-outline" size={18} color={colors.brand} />
          <Text style={styles.secondaryButtonText}>Me interesa</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.commentButton} onPress={() => onInterest("Comentario preparado para la charla.")} testID={`comment-button-${item.id}`}>
          <Ionicons name="chatbubble-outline" size={18} color={colors.muted} />
          <Text style={styles.commentText}>{item.comments}</Text>
        </TouchableOpacity>
      </View>
    </Animated.View>
  );
}

function MapDiscover({ points, chains }) {
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

      <Text style={styles.sectionTitle}>Cadenas premium sugeridas</Text>
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

function BodegaProfile({ profile, offers, wishes }) {
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
          <StatsRow profile={profile} />
        </View>
        {list.length === 0 ? (
          <View style={styles.emptyShelf} testID="empty-bodega-state">
            <Ionicons name="file-tray-outline" size={42} color={colors.muted} />
            <Text style={styles.stateTitle}>Tu bodega está vacía</Text>
            <Text style={styles.stateText}>Agrega lo que ofreces o lo que necesitas para cruzar datos.</Text>
          </View>
        ) : list.map((item, index) => <InventoryRow key={item.id} item={item} index={index} />)}
      </ScrollView>
    </View>
  );
}

function InventoryRow({ item, index }) {
  const icon = iconForImage[item.image_key] || "cube-outline";
  return (
    <Animated.View entering={FadeInDown.delay(index * 65)} style={styles.inventoryRow} testID={`inventory-row-${item.id}`}>
      <View style={styles.inventoryIcon}><Ionicons name={icon} size={24} color={colors.brand} /></View>
      <View style={styles.inventoryCopy}>
        <Text style={styles.inventoryTitle}>{item.title}</Text>
        <Text style={styles.inventoryMeta}>{item.category} · {item.condition} · ${item.estimated_value.toLocaleString("es-MX")}</Text>
        <Text style={styles.inventoryTrade}>Por: {item.exchange_for}</Text>
      </View>
    </Animated.View>
  );
}

function AddItemForm({ onCreated, onNotice }) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState("General");
  const [kind, setKind] = useState("producto");
  const [listingType, setListingType] = useState("oferta");
  const [value, setValue] = useState("");
  const [exchangeFor, setExchangeFor] = useState("");
  const [saving, setSaving] = useState(false);
  const [validation, setValidation] = useState("");

  const submit = async () => {
    Keyboard.dismiss();
    if (!title.trim() || !description.trim() || !exchangeFor.trim()) {
      setValidation("Completa título, descripción y qué aceptas o buscas a cambio.");
      return;
    }
    try {
      setSaving(true);
      setValidation("");
      const response = await fetch(`${API_BASE}/api/items`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title, description, category, kind, listing_type: listingType, estimated_value: Number(value || 0), exchange_for: exchangeFor, condition: kind === "servicio" ? "Servicio" : "Usado", pricing_model: kind === "servicio" ? "por hora o a destajo" : "valor estimado", location: "Mi zona", image_key: "box" }),
      });
      if (!response.ok) throw new Error("No se pudo publicar");
      setTitle("");
      setDescription("");
      setExchangeFor("");
      setValue("");
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
        <LabeledInput label="Qué aceptas o buscas a cambio" value={exchangeFor} onChangeText={setExchangeFor} placeholder="Herramientas, clases, comida, dinero parcial..." multiline testID="item-exchange-input" />
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

function ChatsScreen({ chats }) {
  return (
    <ScrollView style={styles.scroll} contentContainerStyle={styles.chatContent} showsVerticalScrollIndicator={false} testID="chats-screen">
      <Text style={styles.formIntro}>Conversaciones para acordar entregas, cadenas y puntos seguros.</Text>
      {chats.map((chat) => (
        <Pressable key={chat.id} style={styles.chatRow} testID={`chat-row-${chat.id}`} onPress={() => Haptics.selectionAsync()}>
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
  imageScrim: { position: "absolute", left: 0, right: 0, bottom: 0, padding: 16, paddingTop: 52 },
  imageTitle: { color: "#fff", fontSize: 22, fontWeight: "900" },
  imageValue: { color: "rgba(255,255,255,0.86)", fontSize: 14, fontWeight: "700", marginTop: 4 },
  itemDescription: { color: colors.ink, fontSize: 15, lineHeight: 22, marginTop: 14 },
  exchangeBox: { flexDirection: "row", gap: 8, backgroundColor: colors.greenSoft, borderRadius: 16, padding: 12, marginTop: 12 },
  exchangeText: { flex: 1, fontSize: 14, color: colors.dark, lineHeight: 20 },
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
  emptyShelf: { backgroundColor: colors.card, borderRadius: 24, borderWidth: 1, borderColor: colors.line, padding: 24, alignItems: "center", gap: 10 },
  inventoryRow: { backgroundColor: colors.card, borderRadius: 20, borderWidth: 1, borderColor: colors.line, padding: 14, flexDirection: "row", gap: 12 },
  inventoryIcon: { width: 52, height: 52, borderRadius: 18, backgroundColor: colors.brandSoft, alignItems: "center", justifyContent: "center" },
  inventoryCopy: { flex: 1 },
  inventoryTitle: { color: colors.ink, fontSize: 16, fontWeight: "900" },
  inventoryMeta: { color: colors.muted, fontSize: 12, marginTop: 4, fontWeight: "600" },
  inventoryTrade: { color: colors.dark, fontSize: 13, lineHeight: 19, marginTop: 6 },
  formShell: { flex: 1 },
  formContent: { paddingHorizontal: 20, paddingBottom: 110, gap: 14 },
  formIntro: { color: colors.muted, fontSize: 15, lineHeight: 22, marginBottom: 2 },
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
  tabBar: { position: "absolute", left: 0, right: 0, bottom: 0, minHeight: 76, paddingTop: 9, borderTopWidth: 1, borderTopColor: "rgba(229,229,223,0.9)", flexDirection: "row", backgroundColor: "rgba(250,250,248,0.86)" },
  tabButton: { flex: 1, minHeight: 54, alignItems: "center", justifyContent: "center", gap: 3 },
  tabLabel: { color: colors.muted, fontSize: 11, fontWeight: "800" },
  tabLabelActive: { color: colors.brand },
  toast: { position: "absolute", left: 20, right: 20, minHeight: 46, borderRadius: 23, backgroundColor: colors.dark, flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 8, paddingHorizontal: 16 },
  toastText: { color: "#fff", fontWeight: "800", fontSize: 14 },
});
