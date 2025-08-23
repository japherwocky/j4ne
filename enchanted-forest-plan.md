# Enchanted Forest Procedural Generation Plan

This document outlines the rules, procedural generation mechanics, and development framework for creating a procedurally generated Enchanted Forest-style game.

---

## **Game Rules and Design Outline**

### **Overview**
The game is set in a magical forest where players explore enchanted trees, roll dice to move, and claim hidden treasures at the castle. The board is procedurally generated to offer unique layouts in every session, emphasizing strategy and exploration.

---

### **Gameplay Rules**
1. **Procedural Board:**
   - The forest consists of dynamically generated paths, enchanted trees, empty spaces, and the castle.
   - Trees hide treasures randomly assigned at the start of the game.

2. **Movement Mechanics:**
   - Players roll two six-sided dice each turn.
   - Dice total determines the maximum movement points for that turn.
   - Players can split movement points between forward and backward directions.

3. **Tree Exploration:**
   - Players may stop their movement on a tree space to look beneath it.
   - Viewing treasure cards is private to each player.

4. **Treasure Claims:**
   - Players visit the castle to make treasure claims based on the revealed cards.
   - Correct claims earn points, while incorrect claims may have penalties.

5. **Scoring System:**
   - Points are awarded for correctly claimed treasures.
   - Optional leaderboard for multiplayer tracking.

---

## **Procedural Board Generation**

### **Key Elements of the Board**
1. **Forest Paths:**
   - Interconnected paths created procedurally to ensure strategic exploration.
   - Use algorithms like Recursive Backtracking or Depth-First Search for maze-like path generation.

2. **Enchanted Trees:**
   - Randomly scattered across the board (10-15 trees per game).
   - Each tree is reachable and placed thoughtfully to avoid isolation.

3. **Castle:**
   - Centrally located or connected to all major paths.
   - Players must visit it to claim treasures.

4. **Empty Spaces:**
   - Provide breathing room and maneuverability between key locations.

5. **Optional Additions:**
   - Bridges, rivers, and thematic obstacles for visual appeal and gameplay variation.

---

### **Procedural Generation Algorithm**
1. **Grid-Based Design:**
   - Use a grid or hexagonal tile system as the basis for the board.

2. **Path Generation:**
   - Create winding paths using procedural algorithms.
   - Ensure all key locations (trees and castle) are connected.

3. **Tree Placement:**
   - Randomly place trees in accessible spots.

4. **Treasure Assignment:**
   - Randomly assign treasures to trees from a predefined list.

5. **Validation:**
   - Ensure all tiles and spaces follow movement rules.
   - Guarantee that the castle is reachable from all starting positions.

---

## **Web App Planning**

### **Technology Stack**
1. **Frontend:**
   - **HTML5/CSS3**: Structure and styling.
   - **JavaScript Frameworks:**
     - **React.js**: Interactive UI.
     - **D3.js or Konva.js**: Rendering the procedurally generated board.
   - **Canvas API** (optional): Direct board generation in the browser.

2. **Backend:**
   - **Node.js**:
     - Procedural generation logic (if not handled in the frontend).
     - Player movement, treasure logic, dice rolls.
   - **SQLite or MongoDB**: Databases for persistence (treasures, scores, and player state).

3. **Networking:**
   - **WebSockets**: Enable multiplayer real-time play.

---

### **Game Workflow**
1. **Procedural Board Generation:**
   - Generate randomized forest with paths, trees, and the castle.
   - Vary dimensions for difficulty.

2. **Dice Rolling Mechanic:**
   - Simulate dice rolls using random numbers.
   - Display dice visually on the UI.
   - Allow flexible movement on the board.

3. **Tree Memory/Reveal:**
   - Players click tree spaces to view hidden treasures.
   - Implement animations for treasure reveals.

4. **Treasure Claims:**
   - Players make claims at the castle.
   - Treasure cards dynamically served.

5. **Scoring and Leaderboard:**
   - Track claimed treasures and scores per player.
   - Optional multiplayer leaderboard.

---

### **UI Wireframe**
1. **Homepage:**
   - Start game button.
   - Rules and tutorial section.

2. **Game Board:**
   - Display procedurally generated paths, trees, and castle.
   - Sidebar for dice rolls, treasure cards, and scores.

3. **Action Buttons:**
   - Roll Dice, Claim Treasure.

---

### **Multiplayer Option**
1. WebSockets or Socket.IO for simultaneous play.
2. Turn-based mechanics for movement and claiming.

---

### **Funny Backstory:**

#### **Once Upon a Time in the Enchanted Forest**
King Buffleboggle the Bewildered sat glumly on his throne. His castle was grand, his gardens lush, and his crown shiny—but something was missing: treasures! As a self-proclaimed "Collector of Everything Sparkly," the king yearned to fill his treasure halls with rare and magical artifacts.

The problem? Buffleboggle was terrible at finding treasures. He once declared an old potato "The Gemstone of Eternity!" and convinced himself that a particularly shiny rock was a fragment of the moon.

One day, the king hatched a plan. Rather than embarrassing himself with another "treasure hunt disaster," he called upon the bravest (and perhaps quirkiest) adventurers from across the realm. Their mission: venture into the mysterious Enchanted Forest, uncover the secrets hidden within its ancient trees, and return with treasures worthy of the king’s absurdly high standards.

But beware! The Enchanted Forest is not a place for the faint of heart. It’s full of mischievous squirrels, prankster fairies, and trees that talk in riddles. And the king’s treasures aren’t ordinary treasures—they’re absurd treasures like “The Golden Rubber Chicken,” “The Crystalized Boot of Destiny,” and “The Legendary Mystical Toaster.”

Who will outwit the forest’s tricks, impress King Buffleboggle, and earn the title of "Royal Boggle Champion?" Only the cleverest and luckiest adventurer will succeed. Just remember: don’t bring him shiny rocks. He’s still figuring out the moon thing.

#### **Key World-Building Details**
1. **The Enchanted Forest**:
   - A magical place laden with mystical trees that hide treasures.
   - The forest is alive with personality—trees talk, paths shift, and random magical events keep players on their toes.

2. **King Buffleboggle**:
   - An eccentric ruler with a bizarre love for odd treasures.
   - Provides dramatic commentary on players’ treasure finds (e.g., “A golden rubber chicken? How *delightfully useless*! I love it!”).

3. **Absurd Treasures**:
   - Treasures hidden under the trees range from ridiculous (like “The Sapphire Bubblegum”) to whimsical (like “The Wand of Sneezing Sparkles”).
   - Each treasure has fictional lore that players can laugh about.

---

### **Next Steps**
1. Prototype procedural generation.
2. Design wireframes for the web app UI.
3. Build frontend components for board rendering.
4. Set up backend to manage logic, database interactions, and multiplayer features.