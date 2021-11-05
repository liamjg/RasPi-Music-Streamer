class TrackNode(object):
    def __init__(self, level, libindex, track_num, parent):
        self.level = level
        self.libindex = libindex
        self.track_num = track_num
        self.name = "track" + str(track_num)
        self.parent = parent
        self.parent.add_child(self)

    def __repr__(self):
        return self.name

    def preorder(self):
        yield self

class TreeNode(object):
    def __init__(self, level, name, parent=None, children=None):
        self.level = level
        self.name = name
        self.parent = parent
        self.children = []
        if children is not None:
            for child in children:
                self.add_child(child)
        if parent is not None:
            parent.add_child(self)

    def __repr__(self):
        return self.name

    def search_by_name(self,name):
        for search in self.preorder():
            if name == search.name:
                return search

    def set_parent(self, node):
        self.parent = node

    def add_child(self, node):
        if node not in self.children:
            self.children.append(node)

    def sort_tracks(self):
        for iter_num in range(len(self.children)-1,0,-1):
            for idx in range(iter_num):
                if self.children[idx].track_num > self.children[idx+1].track_num:
                    temp = self.children[idx]
                    self.children[idx] = self.children[idx+1]
                    self.children[idx+1] = temp
    
    def sort_children(self):
         for iter_num in range(len(self.children)-1,0,-1):
            for idx in range(iter_num):
                if self.children[idx].name > self.children[idx+1].name:
                    temp = self.children[idx]
                    self.children[idx] = self.children[idx+1]
                    self.children[idx+1] = temp
  
    def preorder(self):
        yield self
        for child in self.children:
            for descendent in child.preorder():
                yield descendent

